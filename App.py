import streamlit as st
import random
from datetime import datetime, timedelta
import io
import zipfile

st.set_page_config(page_title="Sayaç - Mobil & Web", page_icon="⏱️", layout="wide")

# Koyu Tema
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

st.title("⏱️ Sayaç - Toplu Veri Ayıklama ve Paketleme")

# 1. Dosya / Klasör Yükleme Bölümü
st.subheader("1. Dosya ve Klasör Seçimleri")
col1, col2 = st.columns(2)

with col1:
    main_files = st.file_uploader(
        "📂 Ana Klasör / Dosyalar (Birden fazla .txt veya 1 adet .zip seçebilirsiniz)", 
        type=["txt", "zip"], 
        accept_multiple_files=True,
        key="main_files"
    )

with col2:
    filter_file = st.file_uploader(
        "🎯 Ayıklanacak / Filtre Dosyası (.txt)", 
        type=["txt"], 
        key="filter_file"
    )

st.markdown("---")

# 2. Ayarlar Bölümü
st.subheader("2. Personel ve Saat Ayarları")
col3, col4 = st.columns(2)

with col3:
    txt_personel = st.text_area(
        "👥 Personel Listesi (Her satıra 1 isim)", 
        value="Personel 1\nPersonel 2\nPersonel 3",
        height=130
    )

with col4:
    min_shift = st.slider("Minimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=50, step=5)
    max_shift = st.slider("Maksimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=90, step=5)
    paket_boyutu = st.number_input("Paket Başına Satır Sayısı (0 = Bölme, Tek Dosya Yap)", min_value=0, max_value=10000, value=100)

st.markdown("---")

# 3. İşleme ve Ayrıştırma Mantığı
if st.button("⚡ Tüm Dosyaları Tara, Ayıkla ve Paketle"):
    if not main_files:
        st.error("⚠️ Lütfen işlenecek ana dosyaları veya klasör zip dosyasını seçin!")
    else:
        all_lines = []
        dosya_sayisi = 0

        # Yüklenen tüm .txt veya .zip dosyalarını sırayla oku
        for uploaded_file in main_files:
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            with z.open(filename) as f:
                                lines = f.read().decode("utf-8", errors="ignore").splitlines()
                                all_lines.extend(lines)
                                dosya_sayisi += 1
            elif uploaded_file.name.endswith(".txt"):
                lines = uploaded_file.getvalue().decode("utf-8", errors="ignore").splitlines()
                all_lines.extend(lines)
                dosya_sayisi += 1

        st.info(f"📁 Toplam **{dosya_sayisi}** adet dosya başarıyla okundu. Toplam satır: **{len(all_lines)}**")

        # Filtre Dosyasını Oku
        filter_keys = set()
        if filter_file is not None:
            filter_content = filter_file.getvalue().decode("utf-8", errors="ignore").splitlines()
            for f_line in filter_content:
                clean_k = f_line.strip()
                if clean_k:
                    filter_keys.add(clean_k)

        personeller = [p.strip() for p in txt_personel.split("\n") if p.strip()]

        # Satırları Filtreleme ve Saat/Personel Ekleme
        processed_data = []
        for line in all_lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Filtre kontrolü
            if filter_keys and not any(k in line_str for k in filter_keys):
                continue

            personel = random.choice(personeller) if personeller else "Atanmadı"
            kaydirma = random.randint(int(min_shift), int(max_shift))
            yeni_saat = (datetime.now() + timedelta(minutes=kaydirma)).strftime("%H:%M:%S")

            processed_data.append(f"{line_str} | Personel: {personel} | Saat: {yeni_saat}")

        # Çıktıları Paketleme ve İndirme
        if not processed_data:
            st.warning("⚠️ Ayıklanacak kritere uygun veri bulunamadı!")
        else:
            st.success(f"✅ Toplam **{len(processed_data)}** satır ayıklandı ve işlendi.")

            # Dosyaları zip olarak paketle
            if paket_boyutu > 0 and len(processed_data) > paket_boyutu:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                    for i in range(0, len(processed_data), int(paket_boyutu)):
                        chunk = processed_data[i:i + int(paket_boyutu)]
                        chunk_text = "\n".join(chunk)
                        paket_adi = f"sayac_paket_{(i // int(paket_boyutu)) + 1}.txt"
                        zip_out.writestr(paket_adi, chunk_text)

                zip_buffer.seek(0)
                st.download_button(
                    label=f"💾 Ayıklanmış Paketleri İndir (ZIP - {len(processed_data)} Satır)",
                    data=zip_buffer,
                    file_name="ayiklanmis_sayac_paketleri.zip",
                    mime="application/zip"
                )
            else:
                st.download_button(
                    label="💾 Ayıklanmış Dosyayı İndir (.txt)",
                    data="\n".join(processed_data),
                    file_name="ayiklanmis_sayac.txt",
                    mime="text/plain"
                )

            st.subheader("📋 Çıktı Önizleme (İlk 50 Satır)")
            st.text_area("Önizleme", "\n".join(processed_data[:50]), height=250)
