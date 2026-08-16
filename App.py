import streamlit as st
import random
from datetime import datetime, timedelta
import io
import zipfile

st.set_page_config(page_title="Sayaç - Mobil & Web", page_icon="⏱️", layout="wide")

# Özel Koyu Tema Stili
st.markdown("""
    <style>
    .main { background-color: #121212; color: #E0E0E0; }
    .stButton>button { 
        background-color: #1F1F1F; 
        color: #00E676; 
        border: 1px solid #00E676; 
        border-radius: 8px;
        width: 100%;
        font-weight: bold;
    }
    .stDownloadButton>button {
        background-color: #00E676;
        color: #121212;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⏱️ Sayaç - Veri Ayıklama ve Paketleme")

# Adım 1: Dosya Yükleme Alanları
st.subheader("1. Dosya Seçimleri")
col1, col2 = st.columns(2)

with col1:
    main_file = st.file_uploader("📂 1. Ana Dosyayı Seçin (.txt)", type=["txt"], key="main_file")

with col2:
    filter_file = st.file_uploader("🎯 2. Ayıklanacak / Filtre Dosyasını Seçin (.txt)", type=["txt"], key="filter_file")

st.markdown("---")

# Adım 2: Parametreler & Personel Listesi
st.subheader("2. Personel ve Saat Ayarları")
col3, col4 = st.columns(2)

with col3:
    txt_personel = st.text_area(
        "👥 Personel Listesi (Her satıra bir isim)", 
        value="Personel 1\nPersonel 2\nPersonel 3",
        height=130
    )

with col4:
    min_shift = st.slider("Minimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=50, step=5)
    max_shift = st.slider("Maksimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=90, step=5)
    paket_boyutu = st.number_input("Paket Başına Satır Sayısı (0 = Tek Dosya)", min_value=0, max_value=5000, value=50)

st.markdown("---")

# Adım 3: İşlem ve Ayıklama
if st.button("⚡ Verileri Ayıkla, Filtrele ve Paketle"):
    if main_file is None:
        st.error("⚠️ Lütfen önce 'Ana Dosya'yı yükleyin!")
    else:
        # Ana dosya satırlarını oku
        main_content = main_file.getvalue().decode("utf-8", errors="ignore").splitlines()
        
        # Filtre dosyası varsa oku
        filter_keys = set()
        if filter_file is not None:
            filter_content = filter_file.getvalue().decode("utf-8", errors="ignore").splitlines()
            for f_line in filter_content:
                f_clean = f_line.strip()
                if f_clean:
                    filter_keys.add(f_clean)
        
        personeller = [p.strip() for p in txt_personel.split("\n") if p.strip()]
        
        # Süzme ve İşleme Mantığı
        processed_data = []
        for line in main_content:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Filtre dosyası yüklendiyse kontrol et
            if filter_keys:
                # Satır filtredeki anahtarlardan herhangi birini içeriyor mu?
                if not any(k in line_str for k in filter_keys):
                    continue

            # Rastgele Personel ve Zaman Kaydırma
            atanan_personel = random.choice(personeller) if personeller else "Atanmadı"
            kaydirma = random.randint(int(min_shift), int(max_shift))
            yeni_saat = (datetime.now() + timedelta(minutes=kaydirma)).strftime("%H:%M:%S")

            processed_data.append(f"{line_str} | Personel: {atanan_personel} | Saat: {yeni_saat}")

        # Sonuçların Gösterilmesi ve Paketlenmesi
        if not processed_data:
            st.warning("⚠️ Kriterlere veya filtre dosyasına uygun satır bulunamadı!")
        else:
            st.success(f"✅ Toplam {len(processed_data)} satır veri başarıyla ayıklandı ve işlendi.")

            # Paketleme (Dosyalara Bölme) Mantığı
            if paket_boyutu > 0 and len(processed_data) > paket_boyutu:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for i in range(0, len(processed_data), int(paket_boyutu)):
                        chunk = processed_data[i:i + int(paket_boyutu)]
                        chunk_text = "\n".join(chunk)
                        file_name = f"sayac_paket_{(i // int(paket_boyutu)) + 1}.txt"
                        zip_file.writestr(file_name, chunk_text)
                
                zip_buffer.seek(0)
                st.download_button(
                    label=f"💾 Ayıklanmış Paketleri İndir (ZIP - {len(processed_data)} Satır)",
                    data=zip_buffer,
                    file_name="islenmis_sayac_paketleri.zip",
                    mime="application/zip"
                )
            else:
                tek_dosya_metni = "\n".join(processed_data)
                st.download_button(
                    label="💾 Ayıklanmış Dosyayı İndir (.txt)",
                    data=tek_dosya_metni,
                    file_name="islenmis_sayac.txt",
                    mime="text/plain"
                )

            # Önizleme Kutusu
            st.subheader("📋 Çıktı Önizleme (İlk 50 Satır)")
            st.text_area("Önizleme", "\n".join(processed_data[:50]), height=250)
