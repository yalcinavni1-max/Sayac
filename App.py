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
        "🎯 2. Ayıklanacak Lokasyon Listesi (Sayfa1.txt)", 
        type=["txt"], 
        key="filter_file"
    )

with col3:
    personel_file = st.file_uploader(
        "👥 3. Personel Listesi (personel.txt)", 
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
    lokasyon_paket_boyutu = st.number_input("Her Paketteki Lokasyon Sayısı", min_value=1, max_value=500, value=10)

st.markdown("---")

def read_file_safely(byte_content: bytes) -> str:
    """Tüm Unicode, UTF-16, ANSI ve Windows-1254 dosyalarını temizleyerek metne çevirir."""
    # Doğrudan UTF-16 LE kontrolü
    if byte_content.startswith(b'\xff\xfe') or byte_content.startswith(b'\xfe\xff'):
        try:
            return byte_content.decode('utf-16').replace('\ufeff', '')
        except Exception:
            pass
            
    for enc in ['utf-8-sig', 'utf-8', 'windows-1254', 'iso-8859-9', 'latin1']:
        try:
            decoded = byte_content.decode(enc)
            if '\x00' not in decoded:
                return decoded.replace('\ufeff', '')
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Null baytları ayıkla
    clean_bytes = byte_content.replace(b'\x00', b'').replace(b'\xff\xfe', b'')
    return clean_bytes.decode('utf-8', errors='ignore')

def clean_key(text: str) -> str:
    """Metindeki tüm gereksiz boşluk ve özel karakterleri temizler."""
    return re.sub(r'[^A-Z0-9]', '', str(text).strip().upper().replace("\ufeff", "").replace("\x00", ""))

def shift_timestamp_in_line(line: str, minutes_to_add: int) -> str:
    """Satır içindeki SA:gg/aa/yyyy ss:dd:sn zamanını ileri kaydırır."""
    pattern = r'SA:(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})(\.\d+)?'
    match = re.search(pattern, line)
    if match:
        date_part = match.group(1)
        time_part = match.group(2)
        micro_part = match.group(3) or ".000000"
        try:
            full_dt = datetime.strptime(f"{date_part} {time_part}", "%d/%m/%Y %H:%M:%S")
            shifted_dt = full_dt + timedelta(minutes=minutes_to_add)
            return re.sub(pattern, f"SA:{shifted_dt.strftime('%d/%m/%Y %H:%M:%S')}{micro_part}", line)
        except Exception:
            return line
    return line

# 3. Ayıklama ve Paketleme
if st.button("⚡ Lokasyon Bloklarını Ayıkla ve Formatlı Paketle"):
    if not main_files:
        st.error("⚠️ Lütfen ana dosyaları yükleyin!")
    elif filter_file is None:
        st.error("⚠️ Lütfen ayıklanacak lokasyon dosyasını (Sayfa1.txt) yükleyin!")
    elif personel_file is None:
        st.error("⚠️ Lütfen personel dosyasını (personel.txt) yükleyin!")
    else:
        # 1. Personel Listesini Yükle
        p_text = read_file_safely(personel_file.getvalue())
        personeller = [p.strip() for p in p_text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if p.strip()]

        if not personeller:
            st.error("⚠️ Personel listesi boş!")
            st.stop()

        # 2. Ayıklanacak Lokasyon Listesini Yükle (Sayfa1.txt)
        f_text = read_file_safely(filter_file.getvalue())
        f_lines = [f.strip() for f in f_text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if f.strip()]
        
        target_keys = set()
        for raw_target in f_lines:
            c = clean_key(raw_target)
            if c:
                target_keys.add(c)
                if len(c) >= 4:
                    target_keys.add(c[-4:])  # Son 4 hane desteği

        # 3. Ana Dosyaları Oku
        all_raw_texts = []
        dosya_sayisi = 0

        for uploaded_file in main_files:
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            with z.open(filename) as f:
                                all_raw_texts.append(read_file_safely(f.read()))
                                dosya_sayisi += 1
            elif uploaded_file.name.endswith(".txt"):
                all_raw_texts.append(read_file_safely(uploaded_file.getvalue()))
                dosya_sayisi += 1

        st.info(f"📁 **{dosya_sayisi}** adet ana dosya, **{len(personeller)}** personel okundu.")

        # 4. LOCATION ... BEGIN ... ENDL Bloklarını Topla
        location_blocks = {}
        detected_loc_samples = []

        for full_text in all_raw_texts:
            lines = full_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            current_loc = None
            current_items = []
            in_begin = False

            for line in lines:
                l_strip = line.strip()
                if not l_strip:
                    continue

                if l_strip.upper().startswith("LOCATION"):
                    # LOCATION satırından lokasyon kodunu al
                    parts = l_strip.split()
                    if len(parts) >= 2:
                        current_loc = parts[1].strip()
                        if len(detected_loc_samples) < 10:
                            detected_loc_samples.append(current_loc)
                    in_begin = False
                    current_items = []
                elif l_strip.upper() == "BEGIN":
                    in_begin = True
                elif l_strip.upper() == "ENDL":
                    if current_loc and current_items:
                        c_loc = clean_key(current_loc)
                        
                        # Lokasyon arananlar listesinde var mı kontrol et
                        is_match = (c_loc in target_keys) or (len(c_loc) >= 4 and c_loc[-4:] in target_keys)
                        
                        if is_match:
                            if current_loc not in location_blocks:
                                location_blocks[current_loc] = []
                            location_blocks[current_loc].extend(current_items)

                    current_loc = None
                    current_items = []
                    in_begin = False
                elif in_begin:
                    current_items.append(l_strip)

        active_loc_keys = list(location_blocks.keys())

        # 5. Sonuç Kontrolü ve Paketleme
        if not active_loc_keys:
            st.warning("⚠️ Aranan lokasyon blokları eşleşmedi!")
            with st.expander("🔍 Dosya Formatı Kontrolü (Hata Analizi)"):
                st.write("**Sayfa1.txt içinden temizlenen ilk 5 hedef kod:**", list(target_keys)[:5])
                st.write("**Ana dosyalardan okunan ilk 5 LOCATION kodu:**", detected_loc_samples[:5])
        else:
            total_items_count = sum(len(v) for v in location_blocks.values())
            st.success(f"✅ Toplam **{len(active_loc_keys)}** lokasyon ({total_items_count} barkod satırı) başarıyla ayıklandı.")

            # Paketleme Bölümü
            pkg_size = int(lokasyon_paket_boyutu)
            zip_buffer = io.BytesIO()
            paket_ozetleri = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                for i in range(0, len(active_loc_keys), pkg_size):
                    loc_chunk = active_loc_keys[i:i + pkg_size]
                    
                    # Her paket için 1 rastgele personel seç
                    paket_personeli = random.choice(personeller)
                    
                    rand_id = random.randint(100000, 999999)
                    file_name = f"200911{rand_id}.txt"
                    paket_ozetleri.append(f"{file_name} -> {len(loc_chunk)} Lokasyon | Atanan Personel ID: {paket_personeli}")

                    package_text_blocks = []
                    for loc in loc_chunk:
                        # LOCATION başlığına seçilen personeli yaz
                        package_text_blocks.append(f"LOCATION          {loc:<15} {paket_personeli}")
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
