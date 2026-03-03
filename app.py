import streamlit as st
import cv2
import numpy as np

# --- 1. CORE CRYPTO FUNCTIONS ---
@st.cache_data
def arnold_cat_map(image, iterations):
    height, width = image.shape
    N = min(height, width)
    scrambled = np.zeros((N, N), dtype=np.uint8)
    img_square = image[:N, :N]
    for _ in range(iterations):
        for x in range(N):
            for y in range(N):
                new_x = (x + y) % N
                new_y = (x + 2 * y) % N
                scrambled[new_x, new_y] = img_square[x, y]
        img_square = np.copy(scrambled)
    return scrambled

@st.cache_data
def inverse_arnold_cat_map(image, iterations):
    height, width = image.shape
    N = min(height, width)
    restored = np.zeros((N, N), dtype=np.uint8)
    img_square = image[:N, :N]
    for _ in range(iterations):
        for x in range(N):
            for y in range(N):
                orig_x = (2 * x - y) % N
                orig_y = (-x + y) % N
                restored[orig_x, orig_y] = img_square[x, y]
        img_square = np.copy(restored)
    return restored

@st.cache_data
def logistic_map_keystream(x0, r, size):
    keystream = []
    x = x0
    for _ in range(size):
        x = r * x * (1 - x)
        key_byte = int((x * 10**6) % 256)
        keystream.append(key_byte)
    return np.array(keystream, dtype=np.uint8)

@st.cache_data
def diffusion_xor(image, x0, r):
    height, width = image.shape
    total_pixels = height * width
    keystream = logistic_map_keystream(x0, r, total_pixels)
    flat_image = image.flatten()
    encrypted_flat = np.bitwise_xor(flat_image, keystream)
    return encrypted_flat.reshape(height, width)

# --- 2. WEB APP UI SETTINGS ---
st.set_page_config(page_title="Chaos Crypto Pro", page_icon="🔐", layout="wide")

st.title(" Chaos-Based Image Cryptography")
st.markdown("Secure your private images using non-linear dynamical systems")
st.markdown("---")

# --- 3. SIDEBAR (KEYS) ---
st.sidebar.header("Security Keys ⚙️")
st.sidebar.info("both for (Encrypt aur Decrypt) key should be same")
arnold_iterations = st.sidebar.slider("Arnold Map Iterations", 1, 10, 5)
logistic_x0 = st.sidebar.number_input("Secret Key 1 (x0)", value=0.54321, format="%.5f")
logistic_r = st.sidebar.number_input("Secret Key 2 (r)", value=3.99, format="%.2f")

# --- 4. TABS SETUP ---
tab_encrypt, tab_decrypt = st.tabs([" Encrypt Image", " Decrypt Image"])

# ==========================================
#               ENCRYPTION TAB
# ==========================================
with tab_encrypt:
    st.header("Step 1: Hide Your Image")
    
    #  Upload or Camera  option
    input_method = st.radio("from where do get image(Image)", (" Upload from PC", " Take Live Photo"))
    
    enc_file = None
    if input_method == " Upload from PC":
        enc_file = st.file_uploader("Upload an Image to Encrypt", type=["jpg", "png", "jpeg"], key="enc_up")
    else:
        enc_file = st.camera_input("Take a picture to encrypt", key="enc_cam")
    
    if enc_file is not None:
        file_bytes = np.asarray(bytearray(enc_file.read()), dtype=np.uint8)
        opencv_image = cv2.imdecode(file_bytes, 1)
        original_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
        
        orig_h, orig_w = original_image.shape[:2]
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Original Image")
            st.image(original_image, use_container_width=True)
            st.info(f" Note down Original Size for Decryption: Width = {orig_w}, Height = {orig_h}")
            
        if st.button(" Encrypt Now", use_container_width=True):
            with st.spinner('Encrypting using Chaos Theory...'):
                N = max(orig_h, orig_w) 
                padded_image = np.zeros((N, N, 3), dtype=np.uint8)
                padded_image[0:orig_h, 0:orig_w] = original_image
                
                r_chan, g_chan, b_chan = cv2.split(padded_image)
                
                r_scram = arnold_cat_map(r_chan, arnold_iterations)
                g_scram = arnold_cat_map(g_chan, arnold_iterations)
                b_scram = arnold_cat_map(b_chan, arnold_iterations)
                
                r_enc = diffusion_xor(r_scram, logistic_x0, logistic_r)
                g_enc = diffusion_xor(g_scram, logistic_x0, logistic_r)
                b_enc = diffusion_xor(b_scram, logistic_x0, logistic_r)
                
                final_encrypted_img = cv2.merge((r_enc, g_enc, b_enc))
                
                with col2:
                    st.subheader("Encrypted Image")
                    st.image(final_encrypted_img, use_container_width=True)
                    
                    is_success, buffer = cv2.imencode(".png", cv2.cvtColor(final_encrypted_img, cv2.COLOR_RGB2BGR))
                    if is_success:
                        st.download_button(label="📥 Download Encrypted Image", 
                                           data=buffer.tobytes(), 
                                           file_name="encrypted_output.png", 
                                           mime="image/png")
                st.success("Success! Image is now secure.")

# ==========================================
#               DECRYPTION TAB
# ==========================================
with tab_decrypt:
    st.header("Step 2: Restore Your Image")
    dec_file = st.file_uploader("Upload Encrypted Image (White Noise)", type=["png"], key="dec_up")
    
    st.markdown("Enter original image dimensions to remove zero-padding:")
    col_w, col_h = st.columns(2)
    with col_w:
        input_w = st.number_input("Original Width", min_value=1, value=640)
    with col_h:
        input_h = st.number_input("Original Height", min_value=1, value=480)
        
    if dec_file is not None:
        file_bytes = np.asarray(bytearray(dec_file.read()), dtype=np.uint8)
        opencv_image = cv2.imdecode(file_bytes, 1)
        encrypted_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
        
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Encrypted Image")
            st.image(encrypted_image, use_container_width=True)
            
        if st.button(" Decrypt Now", use_container_width=True):
            with st.spinner('Decrypting... Matching Secret Keys...'):
                r_enc, g_enc, b_enc = cv2.split(encrypted_image)
                
                r_res = diffusion_xor(r_enc, logistic_x0, logistic_r)
                g_res = diffusion_xor(g_enc, logistic_x0, logistic_r)
                b_res = diffusion_xor(b_enc, logistic_x0, logistic_r)
                
                r_final = inverse_arnold_cat_map(r_res, arnold_iterations)
                g_final = inverse_arnold_cat_map(g_res, arnold_iterations)
                b_final = inverse_arnold_cat_map(b_res, arnold_iterations)
                
                square_decrypted = cv2.merge((r_final, g_final, b_final))
                
                final_restored_img = square_decrypted[0:input_h, 0:input_w]
                
                with col4:
                    st.subheader("Restored Original Image")
                    st.image(final_restored_img, use_container_width=True)
                    
                    is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(final_restored_img, cv2.COLOR_RGB2BGR))
                    if is_success:
                        st.download_button(label="📥 Download Restored Image", 
                                           data=buffer.tobytes(), 
                                           file_name="restored_output.jpg", 
                                           mime="image/jpeg")
                st.success("Success! Your original image has been restored.")