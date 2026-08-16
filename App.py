import streamlit as st
import random
import re
from datetime import datetime, timedelta
import io
import zipfile

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

# 1. Dosya Seçimleri
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
        "🎯 2. Ayıklanacak Lokasyon Listesi (.txt)", 
        type=["txt"], 
        key="filter_file"
    )

with col3:
    personel_file = st.file_uploader(
        "👥 3. Personel Listesi (.txt)", 
        type=["txt"], 
        key="personel_file"
    )

st.markdown("---")

# 2. Ayarlar
st.subheader("2. Saat ve Paketleme Ayarları")
col4, col5, col6 = st.columns(3)

with col4:
    min_shift = st.slider("Minimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=50, step=5)

with col5:
    max_shift = st.slider("Maksimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=90, step=5)

with col6:
    lokasyon_paket_boyutu = st.number_input("Her Paketteki Lokasyon Sayısı", min_value=1, max_value=500, value=8)

st.markdown("---")

def clean_key(text: str):
    return re.sub(r'[^A-Z0-9]', '', str(text).strip().upper().replace("\ufeff", ""))

def shift_timestamp_in_line(line: str, minutes_to_add: int):
    """Satır içindeki SA:gg/aa/yyyy ss:dd:sn zaman damgasını kaydırır."""
    pattern = r'SA:(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})(\.\d+)?'
    match = re.search(pattern, line)
    if match:
        date_part = match.group(1)
        time_part = match.group(2)
        micro_part = match.group(3) or ".000000"
        try:
            full_dt = datetime.strptime(f"{date_part} {time_part}", "%d/%m/%Y %H:%M:%S")
            shifted_dt = full_dt + timedelta(minutes=minutes_to_add)
            new_time_str = f"SA:{shifted_dt.strftime('%d/%m/%Y %H:%M:%S')}{micro_part}"
            return re.sub(pattern, new_time_str, line)
        except Exception:
            return line
    return line

# 3. Ayıklama ve Paketleme
if st.button("⚡ Lokasyon Bloklarını Ayıkla ve Formatlı Paketle"):
    if not main_files:
        st.error("⚠️ Lütfen ana dosyaları yükleyin!")
    elif filter_file is None:
        st.error("⚠️ Lütfen ayıklanacak lokasyon listesi dosyasını yükleyin!")
    elif personel_file is None:
        st.error("⚠️ Lütfen personel listesi dosyasını yükleyin!")
    else:
        # Personel Listesi
        p_raw = personel_file.getvalue().decode("utf-8", errors="ignore")
        personeller = [p.strip() for p in p_raw.replace("\r\n", "\n").split("\n") if p.strip()]

        if not personeller:
            st.error("⚠️ Personel listesi boş!")
            st.stop()

        # Lokasyon Listesi (Sayfa1.txt)
        f_raw = filter_file.getvalue().decode("utf-8", errors="ignore")
        raw_filter_lines = [f.strip() for f in f_raw.replace("\r\n", "\n").split("\n") if f.strip()]
        
        target_loc_map = {}
        for orig in raw_filter_lines:
            c = clean_key(orig)
            if c:
                target_loc_map[c] = orig
                if len(c) >= 4:
                    target_loc_map[c[-4:]] = orig

        # Ana Dosyaları Oku ve Bloklara Ayır
        location_blocks = {}  # { orig_loc_name: [satirlar] }

        for uploaded_file in main_files:
            file_texts = []
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            with z.open(filename) as f:
                                file_texts.append(f.read().decode("utf-8", errors="ignore"))
            elif uploaded_file.name.endswith(".txt"):
                file_texts.append(uploaded_file.getvalue().decode("utf-8", errors="ignore"))

            # Her dosyanın içeriğini LOCATION ... BEGIN ... ENDL bloklarına böl
            for text_content in file_texts:
                lines = text_content.replace("\r\n", "\n").split("\n")
                current_loc = None
                current_items = []
                in_begin = False

                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue

                    if line_clean.startswith("LOCATION"):
                        parts = line_clean.split()
                        if len(parts) >= 2:
                            current_loc = parts[1].strip()
                        in_begin = False
                        current_items = []
                    elif line_clean == "BEGIN":
                        in_begin = True
                    elif line_clean == "ENDL":
                        if current_loc and current_items:
                            # Lokasyon eşleşiyor mu kontrol et
                            clean_l = clean_key(current_loc)
                            matched_target = None
                            if clean_l in target_loc_map:
                                matched_target = target_loc_map[clean_l]
                            elif len(clean_l) >= 4 and clean_l[-4:] in target_loc_map:
                                matched_target = target_loc_map[clean_l[-4:]]

                            if matched_target:
                                if matched_target not in location_blocks:
                                    location_blocks[matched_target] = []
                                location_blocks[matched_target].extend(current_items)
                        
                        current_loc = None
                        current_items = []
                        in_begin = False
                    elif in_begin:
                        current_items.append(line)

        # Ayıklanan Lokasyonlar
        active_loc_keys = list(location_blocks.keys())

        if not active_loc_keys:
            st.warning("⚠️ Aranan lokasyon blokları ana dosyalarda bulunamadı!")
        else:
            total_items_count = sum(len(v) for v in location_blocks.values())
            st.success(f"✅ Toplam **{len(active_loc_keys)}** lokasyona ait **{total_items_count}** barkod satırı başarıyla ayıklandı.")

            # Paketleme ve ZIP Oluşturma
            pkg_size = int(lokasyon_paket_boyutu)
            zip_buffer = io.BytesIO()
            paket_ozetleri = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                for i in range(0, len(active_loc_keys), pkg_size):
                    loc_chunk = active_loc_keys[i:i + pkg_size]
                    
                    # Her paket için 1 rastgele personel
                    paket_personeli = random.choice(personeller)
                    
                    # 200911XXXXXX.txt formatında dosya ismi
                    rand_id = random.randint(100000, 999999)
                    file_name = f"200911{rand_id}.txt"
                    paket_ozetleri.append(f"{file_name} -> {len(loc_chunk)} Lokasyon | Personel: {paket_personeli}")

                    # Paket Metnini Blok Yapısında Oluştur
                    package_text_blocks = []
                    for loc in loc_chunk:
                        # LOCATION başlığı
                        loc_header = f"LOCATION          {loc:<15} {paket_personeli}"
                        package_text_blocks.append(loc_header)
                        package_text_blocks.append("BEGIN")
                        
                        # Satırlar ve Saat Kaydırma
                        for item in location_blocks[loc]:
                            kaydirma = random.randint(int(min_shift), int(max_shift))
                            shifted_line = shift_timestamp_in_line(item, kaydirma)
                            package_text_blocks.append(shifted_line)
                            
                        package_text_blocks.append("ENDL")

                    file_content = "\n".join(package_text_blocks)
                    zip_out.writestr(file_name, file_content)

            zip_buffer.seek(0)

            # İndirme Butonu
            st.download_button(
                label=f"💾 Formatlı Paketleri İndir (ZIP - {len(paket_ozetleri)} Adet .txt Dosyası)",
                data=zip_buffer,
                file_name="islenmis_sayac_paketleri.zip",
                mime="application/zip"
            )

            # Paket Dağılım Listesi
            st.subheader("📦 Oluşturulan Paketler")
            for ozet in paket_ozetleri:
                st.write(f"- `{ozet}`")
