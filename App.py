import streamlit as st
import random
import re
from datetime import datetime, timedelta
import io
import zipfile

st.set_page_config(page_title="Sayaç - Toplu Veri Ayıklama ve Paketleme", page_icon="⏱️", layout="wide")

# Koyu Tema Stili
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

# 1. Dosya Seçimleri (3 Alan)
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
        "👥 3. Personel Listesi (.txt)", 
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
    lokasyon_paket_boyutu = st.number_input("Her Paketteki Lokasyon Sayısı (Örn: 8)", min_value=1, max_value=500, value=8)

st.markdown("---")

def clean_code(text: str):
    """Karakterleri sadeleştirip büyük harfe çevirir."""
    return re.sub(r'[^A-Z0-9]', '', str(text).strip().upper().replace("\ufeff", ""))

# 3. Ayıklama ve Paketleme Mantığı
if st.button("⚡ Lokasyonları Grupla ve Paketlere Böl (.txt)"):
    if not main_files:
        st.error("⚠️ Lütfen ana dosyaları yükleyin!")
    elif filter_file is None:
        st.error("⚠️ Lütfen ayıklanacak lokasyon dosyasını yükleyin!")
    elif personel_file is None:
        st.error("⚠️ Lütfen personel dosyasını yükleyin!")
    else:
        # Personel Listesini Oku
        p_raw = personel_file.getvalue().decode("utf-8", errors="ignore")
        personeller = [p.strip() for p in p_raw.replace("\r\n", "\n").split("\n") if p.strip()]

        if not personeller:
            st.error("⚠️ Personel listesi boş!")
            st.stop()

        # Lokasyon Filtre Dosyasını Oku (Sırasını Koru)
        f_raw = filter_file.getvalue().decode("utf-8", errors="ignore")
        raw_target_locs = [f.strip() for f in f_raw.replace("\r\n", "\n").split("\n") if f.strip()]
        
        # Lokasyon Anahtarları Oluştur
        target_map = {}
        for orig_loc in raw_target_locs:
            cleaned = clean_code(orig_loc)
            if cleaned:
                target_map[cleaned] = orig_loc
                if len(cleaned) >= 4:
                    target_map[cleaned[-4:]] = orig_loc

        # Ana Dosyaları Oku
        all_lines = []
        dosya_sayisi = 0

        for uploaded_file in main_files:
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            with z.open(filename) as f:
                                lines = f.read().decode("utf-8", errors="ignore").replace("\r\n", "\n").split("\n")
                                all_lines.extend(lines)
                                dosya_sayisi += 1
            elif uploaded_file.name.endswith(".txt"):
                lines = uploaded_file.getvalue().decode("utf-8", errors="ignore").replace("\r\n", "\n").split("\n")
                all_lines.extend(lines)
                dosya_sayisi += 1

        st.info(f"📁 **{dosya_sayisi}** adet dosya, **{len(personeller)}** personel okundu. Toplam taranan satır: **{len(all_lines)}**")

        # Her Lokasyona Ait Satırları Toplama (Sözlük)
        grouped_by_loc = {orig: [] for orig in raw_target_locs}

        for line in all_lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            line_upper = line_clean.upper()
            line_normalized = clean_code(line_clean)

            # Satırdaki DP/RY kodlarını veya tam eşleşmeyi tespit et
            found_loc = None
            
            # 1. DP veya RY son 4 hanesi
            loc_matches = re.findall(r'(?:DP|RY)[A-Z0-9_-]*', line_upper)
            for loc in loc_matches:
                c = clean_code(loc)
                if len(c) >= 4 and c[-4:] in target_map:
                    found_loc = target_map[c[-4:]]
                    break

            # 2. Genel Eşleşme
            if not found_loc:
                for k, orig in target_map.items():
                    if k in line_normalized:
                        found_loc = orig
                        break

            if found_loc and found_loc in grouped_by_loc:
                grouped_by_loc[found_loc].append(line_clean)

        # Sadece içi dolu olan (veri bulunan) lokasyonları al
        active_locations = [loc for loc, items in grouped_by_loc.items() if len(items) > 0]

        if not active_locations:
            st.warning("⚠️ Aranan lokasyonlara ait hiçbir satır bulunamadı!")
        else:
            total_found_lines = sum(len(grouped_by_loc[l]) for l in active_locations)
            st.success(f"✅ Toplam **{len(active_locations)}** lokasyona ait **{total_found_lines}** satır veri ayrıştırıldı.")

            # Paketleme Bölümü
            pkg_size = int(lokasyon_paket_boyutu)
            zip_buffer = io.BytesIO()
            paket_listesi = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                # Lokasyonları seçilen boyutta (örn: 8'erli) gruplara böl
                for i in range(0, len(active_locations), pkg_size):
                    loc_group = active_locations[i:i + pkg_size]
                    
                    # Her paket dosyasına 1 adet rastgele personel ata
                    paket_personeli = random.choice(personeller)
                    
                    # 200911XXXXXX.txt formatında dosya ismi
                    rand_id = random.randint(100000, 999999)
                    file_name = f"200911{rand_id}.txt"
                    paket_listesi.append(f"{file_name} -> {len(loc_group)} Lokasyon ({', '.join(loc_group)})")

                    # Lokasyonların tüm satırlarını tek bir paket dosyasına topla
                    package_lines = []
                    for loc in loc_group:
                        for item in grouped_by_loc[loc]:
                            kaydirma = random.randint(int(min_shift), int(max_shift))
                            yeni_saat = (datetime.now() + timedelta(minutes=kaydirma)).strftime("%H:%M:%S")
                            package_lines.append(f"{item} | {paket_personeli} | {yeni_saat}")

                    # Tek bir .txt dosyası olarak zip'e yaz
                    file_content = "\n".join(package_lines)
                    zip_out.writestr(file_name, file_content)

            zip_buffer.seek(0)

            # İndirme Butonu
            st.download_button(
                label=f"💾 Ayıklanmış Paketleri İndir (ZIP - Toplam {len(paket_listesi)} Adet Ayrı .txt)",
                data=zip_buffer,
                file_name="ayiklanmis_sayac_paketleri.zip",
                mime="application/zip"
            )

            # Paket Dağılım Listesi
            st.subheader("📦 Oluşturulan Paketler ve İçerdiği Lokasyonlar")
            for p_info in paket_listesi:
                st.write(f"- `{p_info}`")
