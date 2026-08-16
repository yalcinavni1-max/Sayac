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

# 1. Dosya ve Klasör Seçimleri
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
        value="39703679824\n25547157130\n26881866566",
        height=130
    )

with col4:
    min_shift = st.slider("Minimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=50, step=5)
    max_shift = st.slider("Maksimum Saat Kaydırma (Dakika)", min_value=10, max_value=180, value=90, step=5)
    paket_boyutu = st.number_input("Paket Başına Satır Sayısı (0 = Bölme, Tek Dosya Yap)", min_value=0, max_value=10000, value=8)

st.markdown("---")

def normalize_key(key: str):
    """Lokasyon kodunu temizler ve varsa son 4 hanesini/esas kodu çeker."""
    k = key.strip().upper().replace("\ufeff", "")
    # Eğer DP veya RY ile başlıyorsa veya en az 4 karakterse son 4 hanesini de dahil et
    digits_only = re.sub(r'[^A-Z0-9]', '', k)
    return digits_only

# 3. İşleme Mantığı
if st.button("⚡ Tüm Dosyaları Tara, Ayıkla ve Paketle"):
    if not main_files:
        st.error("⚠️ Lütfen işlenecek ana dosyaları seçin!")
    else:
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

        st.info(f"📁 Toplam **{dosya_sayisi}** adet dosya başarıyla okundu. Toplam satır: **{len(all_lines)}**")

        # Filtre Listesini Hazırla
        raw_filter_keys = []
        normalized_filter_keys = set()
        last_4_keys = set()

        if filter_file is not None:
            f_raw = filter_file.getvalue().decode("utf-8", errors="ignore")
            f_lines = f_raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            for f_line in f_lines:
                clean_k = f_line.strip()
                if clean_k:
                    raw_filter_keys.append(clean_k)
                    norm = normalize_key(clean_k)
                    normalized_filter_keys.add(norm)
                    if len(norm) >= 4:
                        last_4_keys.add(norm[-4:])

        personeller = [p.strip() for p in txt_personel.split("\n") if p.strip()]

        processed_data = []
        for line in all_lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Filtre Eşleme Mantığı (DP/RY ve Son 4 Hane Desteği)
            if normalized_filter_keys:
                line_upper = line_str.upper()
                line_normalized = normalize_key(line_str)
                
                # 1. Tam veya alt dize eşleşmesi
                matched = any(k in line_upper for k in normalized_filter_keys)
                
                # 2. DP veya RY lokasyon kodlarının son 4 hanesi üzerinden eşleşme
                if not matched and last_4_keys:
                    # DP veya RY ile başlayan kodları bul (örn: DP1234, RY-5678 vb.)
                    loc_matches = re.findall(r'(?:DP|RY)[A-Z0-9_-]*', line_upper)
                    for loc in loc_matches:
                        clean_loc = re.sub(r'[^A-Z0-9]', '', loc)
                        if len(clean_loc) >= 4 and clean_loc[-4:] in last_4_keys:
                            matched = True
                            break
                
                # 3. Satırdaki herhangi bir 4 haneli kod eşleşmesi
                if not matched and last_4_keys:
                    for l4 in last_4_keys:
                        if l4 in line_normalized:
                            matched = True
                            break

                if not matched:
                    continue

            # Personel ve Saat Kaydırma
            personel = random.choice(personeller) if personeller else "Atanmadı"
            kaydirma = random.randint(int(min_shift), int(max_shift))
            yeni_saat = (datetime.now() + timedelta(minutes=kaydirma)).strftime("%H:%M:%S")

            processed_data.append(f"{line_str} | {personel} | {yeni_saat}")

        # Çıktı ve İndirme
        if not processed_data:
            st.warning("⚠️ Ayıklanacak kritere uygun veri bulunamadı!")
            with st.expander("🔍 Karşılaştırma Formatlarını İnceleyin (Hata Analizi)"):
                st.write("**Filtre Dosyasından İlk 5 Satır:**", raw_filter_keys[:5])
                st.write("**Ana Dosyalardan İlk 3 Satır:**", [l.strip() for l in all_lines[:3] if l.strip()])
        else:
            st.success(f"✅ Toplam **{len(processed_data)}** satır başarıyla ayıklandı ve işlendi.")

            # Paketleme
            if paket_boyutu > 0 and len(processed_data) > paket_boyutu:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                    total_paket = (len(processed_data) + int(paket_boyutu) - 1) // int(paket_boyutu)
                    for i in range(0, len(processed_data), int(paket_boyutu)):
                        chunk = processed_data[i:i + int(paket_boyutu)]
                        chunk_text = "\n".join(chunk)
                        paket_no = (i // int(paket_boyutu)) + 1
                        paket_adi = f"sayac_paket_{paket_no}.txt"
                        zip_out.writestr(paket_adi, chunk_text)

                zip_buffer.seek(0)
                st.download_button(
                    label=f"💾 Ayıklanmış Paketleri İndir (ZIP - Toplam {total_paket} Paket / {len(processed_data)} Satır)",
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
