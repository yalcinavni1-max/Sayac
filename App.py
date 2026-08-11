import streamlit as st
import random
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Sayaç Mobil", page_icon="⏱️", layout="centered")

# Karanlık Tema Şablonu
st.markdown("""
    <style>
    .main { background-color: #121212; color: #E0E0E0; }
    .stButton>button { background-color: #1F1F1F; color: #00E676; border: 1px solid #00E676; width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.title("⏱️ Sayaç - Mobil Veri İşleme")

# 1. Ana Dosya Yükleme
uploaded_file = st.file_uploader("📂 İşlenecek .txt Dosyasını Seçin", type=["txt"])

if uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.splitlines()
    st.success(f"✅ {len(lines)} satır veri yüklendi.")

    st.subheader("⚙️ İşlem Ayarları")
    
    # Ayarlar
    personeller = st.text_area("Personel Listesi (Her satıra bir isim)", "Personel A\nPersonel B\nPersonel C")
    personel_listesi = [p.strip() for p in personeller.split("\n") if p.strip()]
    
    col1, col2 = st.columns(2)
    with col1:
        min_shift = st.number_input("Min Kaydırma (Dk)", value=50, step=5)
    with col2:
        max_shift = st.number_input("Maks Kaydırma (Dk)", value=90, step=5)

    if st.button("⚡ Verileri Ayıkla ve İşle"):
        processed_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Personel ve Saat Kaydırma Mantığı
            atanan = random.choice(personel_listesi) if personel_listesi else "Atanmadı"
            kaydirma = random.randint(int(min_shift), int(max_shift))
            islem_saati = (datetime.now() + timedelta(minutes=kaydirma)).strftime("%H:%M:%S")
            
            processed_lines.append(f"{line_str} | Personel: {atanan} | Saat: {islem_saati}")

        result_text = "\n".join(processed_lines)
        
        st.subheader("📋 Çıktı Önizleme")
        st.text_area("İşlenmiş Veri", result_text, height=200)

        # Doğrudan Telefona .txt Olarak İndirme
        st.download_button(
            label="💾 İşlenmiş Dosyayı İndir (.txt)",
            data=result_text,
            file_name="islenmis_sayac_verisi.txt",
            mime="text/plain"
        )
