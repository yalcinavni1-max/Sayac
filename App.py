import streamlit as st
import random
import re
from datetime import datetime, timedelta
import io
import zipfile
from collections import defaultdict

st.set_page_config(page_title="Sayaç - Toplu Veri Ayıklama ve Paketleme", page_icon="⏱️", layout="wide")

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

# 1. Dosya Seçimleri Bölümü (3 Dosya Alanı)
st.subheader("1. Dosya ve Klasör Seçimleri")
col1, col2, col3 = st.columns(3)

with col1:
    main_files = st.file_uploader(
        "📂 1. Ana Dosyalar / Klasör (.txt veya .zip)", 
        type=["txt", "zip"], 
        accept_multiple_files=True,
        key="main_files"
    )

with col2:
    filter_file = st.file_uploader(
        "🎯 2. Ayıklanacak Lokasyon Dosyası (.txt)", 
        type=["txt"], 
        key="filter_file"
    )

with col3:
    personel_file = st.file_uploader(
        "👥 3. Personel Listesi Dosyası (.txt)", 
        type=["txt"], 
        key="personel_file"
    )

st.markdown("---")

# 2. Ayarlar Bölümü
st.subheader("2. Saat ve Paketleme Ayarları")
col4, col5, col6 = st.columns(3)

with col4:
    min_shift = st.slider("Minimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=50, step=5)

with col5:
    max_shift = st.slider("Maksimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=90, step=5)

with col6:
    lokasyon_paket_boyutu = st.number_input("Paket Başına Lokasyon Sayısı", min_value=1, max_value=500, value=8)

st.markdown("---")

def normalize_key(key: str):
    k = key.strip().upper().replace("\ufeff", "")
    return re.sub(r'[^A-Z0-9]', '', k)

# 3. İşleme ve Paketleme
if st.button("⚡ Lokasyonları Ayıkla ve Formatlı İsimlerle Paketle"):
    if not main_files:
        st.error("⚠️ Lütfen işlenecek ana dosyaları seçin!")
    elif filter_file is None:
        st.error("⚠️ Lütfen ayıklanacak lokasyon dosyasını (Sayfa1.txt) seçin!")
    elif personel_file is None:
        st.error("⚠️ Lütfen personel listesi dosyasını (.txt) seçin!")
    else:
        # Personel Listesini Oku
        p_raw = personel_file.getvalue().decode("utf-8", errors="ignore")
        p_lines = p_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        personeller = [p.strip() for p in p_lines if p.strip()]

        if not personeller:
            st.error("⚠️ Personel dosyası boş veya okunamadı!")
            st.stop()

        all_lines = []
        dosya_sayisi = 0

        for uploaded_file in main_files:
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            with z.open(filename) as f:
                                content = f.read().decode("utf-8", errors="ignore")
                                lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                                all_lines.extend(lines)
                                dosya_sayisi += 1
            elif uploaded_file.name.endswith(".txt"):
                content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
                lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                all_lines.extend(lines)
                dosya_sayisi += 1

        st.info(f"📁 **{dosya_sayisi}** adet ana dosya, **{len(personeller)}** adet personel yüklendi. Toplam satır: **{len(all_lines)}**")

        # Filtre Lokasyonlarını Oku
        f_raw = filter_file.getvalue().decode("utf-8", errors="ignore")
        f_lines = f_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        
        target_lookup = {}
        for f_line in f_lines:
            clean_k = f_line.strip()
            if clean_k:
                norm = normalize_key(clean_k)
                target_lookup[norm] = clean_k
                if len(norm) >= 4:
                    target_lookup[norm[-4:]] = clean_k

        # Lokasyon bazlı gruplama
        grouped_data = defaultdict(list)
        
        for line in all_lines:
            line_str = line.strip()
            if not line_str:
                continue

            line_upper = line_str.upper()
            line_norm = normalize_key(line_str)
            matched_loc_name = None

            for norm_k, orig_name in target_lookup.items():
                if norm_k in line_norm:
                    matched_loc_name = orig_name
                    break

            if not matched_loc_name:
                loc_matches = re.findall(r'(?:DP|RY)[A-Z0-9_-]*', line_upper)
                for loc in loc_matches:
                    clean_loc = normalize_key(loc)
                    if len(clean_loc) >= 4 and clean_loc[-4:] in target_lookup:
                        matched_loc_name = target_lookup[clean_loc[-4:]]
                        break

            if matched_loc_name:
                grouped_data[matched_loc_name].append(line_str)

        matched_loc_list = list(grouped_data.keys())

        if not matched_loc_list:
            st.warning("⚠️ Ayıklanacak lokasyonlara ait veri bulunamadı!")
        else:
            total_lines = sum(len(v) for v in grouped_data.values())
            st.success(f"✅ Toplam **{len(matched_loc_list)}** lokasyon ({total_lines} satır veri) başarıyla eşleşti.")

            pkg_size = int(lokasyon_paket_boyutu)
            zip_buffer = io.BytesIO()
            generated_file_names = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                for i in range(0, len(matched_loc_list), pkg_size):
                    loc_chunk = matched_loc_list[i:i + pkg_size]
                    
                    # Bu paketteki tüm satırlara atanacak tek bir personel seç
                    paket_personeli = random.choice(personeller)
                    
                    # 200911XXXXXX.txt formatında dosya ismi
                    random_suffix = random.randint(100000, 999999)
                    file_name = f"200911{random_suffix}.txt"
                    generated_file_names.append(file_name)

                    packet_lines = []
                    for loc in loc_chunk:
                        for raw_item in grouped_data[loc]:
                            kaydirma = random.randint(int(min_shift), int(max_shift))
                            yeni_saat = (datetime.now() + timedelta(minutes=kaydirma)).strftime("%H:%M:%S")
                            packet_lines.append(f"{raw_item} | {paket_personeli} | {yeni_saat}")

                    packet_content = "\n".join(packet_lines)
                    zip_out.writestr(file_name, packet_content)

            zip_buffer.seek(0)
            st.download_button(
                label=f"💾 Paketleri İndir (ZIP - Toplam {len(generated_file_names)} Dosya)",
                data=zip_buffer,
                file_name="islenmis_sayac_paketleri.zip",
                mime="application/zip"
            )

            st.subheader("📋 Oluşturulan .txt Dosya İsimleri")
            st.write(generated_file_names)
