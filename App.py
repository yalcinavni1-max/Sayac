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

def read_file_safely(byte_content: bytes) -> str:
    """Türkçe karakter ve ANSI/UTF-8 uyumluluğu için güvenli okuma."""
    for enc in ['utf-8-sig', 'utf-8', 'iso-8859-9', 'windows-1254', 'latin1']:
        try:
            return byte_content.decode(enc)
        except UnicodeDecodeError:
            continue
    return byte_content.decode('utf-8', errors='ignore')

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
        st.error("⚠️ Lütfen ayıklanacak lokasyon listesi dosyasını (Sayfa1.txt) yükleyin!")
    elif personel_file is None:
        st.error("⚠️ Lütfen personel listesi dosyasını yükleyin!")
    else:
        # Personel Listesi
        p_raw = read_file_safely(personel_file.getvalue())
        personeller = [p.strip() for p in p_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n") if p.strip()]

        if not personeller:
            st.error("⚠️ Personel listesi boş!")
            st.stop()

        # Lokasyon Filtre Listesi
        f_raw = read_file_safely(filter_file.getvalue())
        raw_filter_lines = [f.strip() for f in f_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n") if f.strip()]
        
        target_keys = set()
        for orig in raw_filter_lines:
            c = clean_key(orig)
            if c:
                target_keys.add(c)
                if len(c) >= 4:
                    target_keys.add(c[-4:])

        # Ana Dosyaları Oku
        file_contents = []
        dosya_sayisi = 0

        for uploaded_file in main_files:
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            with z.open(filename) as f:
                                file_contents.append(read_file_safely(f.read()))
                                dosya_sayisi += 1
            elif uploaded_file.name.endswith(".txt"):
                file_contents.append(read_file_safely(uploaded_file.getvalue()))
                dosya_sayisi += 1

        st.info(f"📁 **{dosya_sayisi}** adet dosya, **{len(personeller)}** personel okundu.")

        # Blokları regex ile LOCATION ... BEGIN ... ENDL şeklinde doğrudan yakala
        location_blocks = {}
        detected_locations_debug = []

        # Esnek Regex: LOCATION ile başlayan, sonra BEGIN ve ENDL arasında kalan tüm blok
        block_pattern = re.compile(
            r'LOCATION\s+([^\r\n\t ]+)[^\r\n]*\r?\n\s*BEGIN\r?\n(.*?)\r?\n\s*ENDL',
            re.DOTALL | re.IGNORECASE
        )

        for text_content in file_contents:
            matches = block_pattern.findall(text_content)
            for raw_loc_code, body in matches:
                clean_loc = clean_key(raw_loc_code)
                if len(detected_locations_debug) < 10:
                    detected_locations_debug.append(raw_loc_code)

                # Filtre kontrolü (Tam kod veya son 4 hane)
                is_match = False
                if clean_loc in target_keys:
                    is_match = True
                elif len(clean_loc) >= 4 and clean_loc[-4:] in target_keys:
                    is_match = True

                if is_match:
                    body_lines = [b.strip() for b in body.split("\n") if b.strip()]
                    if raw_loc_code not in location_blocks:
                        location_blocks[raw_loc_code] = []
                    location_blocks[raw_loc_code].extend(body_lines)

        active_loc_keys = list(location_blocks.keys())

        if not active_loc_keys:
            st.warning("⚠️ Aranan lokasyon blokları ana dosyalarda bulunamadı!")
            with st.expander("🔍 Dosya Formatı Kontrolü (Neden Eşleşmedi?)"):
                st.write("**Sayfa1.txt içindeki aranan ilk 5 kod:**", raw_filter_lines[:5])
                st.write("**Ana dosyalardan okunan ilk 5 LOCATION kodu:**", detected_locations_debug[:5])
        else:
            total_items_count = sum(len(v) for v in location_blocks.values())
            st.success(f"✅ Toplam **{len(active_loc_keys)}** lokasyon ({total_items_count} barkod satırı) başarıyla ayıklandı.")

            # Paketleme ve ZIP
            pkg_size = int(lokasyon_paket_boyutu)
            zip_buffer = io.BytesIO()
            paket_ozetleri = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                for i in range(0, len(active_loc_keys), pkg_size):
                    loc_chunk = active_loc_keys[i:i + pkg_size]
                    paket_personeli = random.choice(personeller)
                    
                    rand_id = random.randint(100000, 999999)
                    file_name = f"200911{rand_id}.txt"
                    paket_ozetleri.append(f"{file_name} -> {len(loc_chunk)} Lokasyon | Personel: {paket_personeli}")

                    package_text_blocks = []
                    for loc in loc_chunk:
                        loc_header = f"LOCATION          {loc:<15} {paket_personeli}"
                        package_text_blocks.append(loc_header)
                        package_text_blocks.append("BEGIN")
                        
                        for item in location_blocks[loc]:
                            kaydirma = random.randint(int(min_shift), int(max_shift))
                            shifted_line = shift_timestamp_in_line(item, kaydirma)
                            package_text_blocks.append(shifted_line)
                            
                        package_text_blocks.append("ENDL")

                    file_content = "\n".join(package_text_blocks)
                    zip_out.writestr(file_name, file_content)

            zip_buffer.seek(0)

            st.download_button(
                label=f"💾 Formatlı Paketleri İndir (ZIP - Toplam {len(paket_ozetleri)} Adet .txt Dosyası)",
                data=zip_buffer,
                file_name="islenmis_sayac_paketleri.zip",
                mime="application/zip"
            )

            st.subheader("📦 Oluşturulan Paketler")
            for ozet in paket_ozetleri:
                st.write(f"- `{ozet}`")
