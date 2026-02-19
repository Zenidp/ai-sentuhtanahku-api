import streamlit as st
import requests
import uuid

# --- KONFIGURASI ---
# Ganti dengan URL Render Anda yang sudah aktif
API_URL = "https://ai-sentuhtanahku-api.onrender.com/api/chat"

# Judul & Ikon Halaman
st.set_page_config(page_title="Sentuh Tanahku AI", page_icon="🏛️")

# Header Tampilan
st.title("🏛️ Asisten Virtual Sentuh Tanahku")
st.markdown("Tanyakan apa saja seputar layanan pertanahan, syarat sertifikat, atau biaya PNBP.")

# --- SESSION STATE (Agar chat tidak hilang saat enter) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --- TAMPILKAN RIWAYAT CHAT ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- INPUT USER ---
if prompt := st.chat_input("Ketik pertanyaan Anda di sini..."):
    # 1. Tampilkan pertanyaan user
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Kirim ke API Render (Backend Anda)
    with st.chat_message("assistant"):
        with st.spinner("Sedang membuka dokumen BPN..."):
            try:
                payload = {
                    "pesan": prompt,
                    "session_id": st.session_state.session_id
                }
                response = requests.post(API_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    jawaban_ai = data.get("jawaban", "Maaf, tidak ada jawaban.")
                    
                    # Tampilkan Jawaban
                    st.markdown(jawaban_ai)
                    
                    # Tampilkan Sumber (Jika ada)
                    sumber_docs = data.get("sumber", [])
                    if sumber_docs:
                        st.divider()
                        st.caption(f"📚 Sumber Referensi: {', '.join(sumber_docs)}")
                    
                    # Simpan ke riwayat
                    st.session_state.messages.append({"role": "assistant", "content": jawaban_ai})
                else:
                    st.error(f"Error API: {response.status_code}")
            except Exception as e:
                st.error(f"Gagal terhubung ke server: {e}")