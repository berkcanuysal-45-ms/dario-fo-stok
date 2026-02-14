# main.py - KAYIT SİLME ÖZELLİĞİ EKLENMİŞ VERSİYON
import streamlit as st
import db

st.set_page_config(page_title="Dario Fo Roastery", layout="wide")
st.title("☕ Dario Fo - Akıllı Stok")

# Verileri Çek
df = db.verileri_getir()

# --- LİSTELERİ HAZIRLA ---
mevcut_cariler = []
mevcut_urunler = []
if not df.empty:
    if "Cari Adı" in df.columns:
        mevcut_cariler = sorted([str(x) for x in df["Cari Adı"].unique() if str(x).strip() not in ["", "-"]])
    if "Ürün" in df.columns:
        mevcut_urunler = sorted([str(x) for x in df["Ürün"].unique() if str(x).strip() not in ["", "-"]])

cari_listesi = ["➕ YENİ CARİ EKLE..."] + mevcut_cariler
urun_listesi = ["➕ YENİ ÜRÜN EKLE..."] + mevcut_urunler

# Yardımcı Fonksiyon
def akilli_secim(etiket, liste, key_ozel):
    secim = st.selectbox(etiket, liste, key=f"sel_{key_ozel}")
    if "YENİ" in str(secim):
        return st.text_input(f"Yeni {etiket} Giriniz:", key=f"txt_{key_ozel}")
    return secim

# --- YAN MENÜ ---
st.sidebar.header("📝 İşlem Seçimi")
secenek = st.sidebar.radio("Ne Yapacaksınız?", 
    ["Stok Hareketi (Alım/Satım)", "Nakit İşlemi (Ödeme/Tahsilat)", "🔥 Kavurma (Üretim)", "🗑️ Kayıt Sil / Düzelt"])

# 1. MODÜL: STOK
if secenek == "Stok Hareketi (Alım/Satım)":
    st.sidebar.subheader("Hızlı Alım/Satım")
    with st.sidebar.form("stok"):
        cari = akilli_secim("Cari", cari_listesi, "stok_cari")
        urun = akilli_secim("Ürün", urun_listesi, "stok_urun")
        tip = st.selectbox("Yön", ["Mal Alım (Stok Giriş)", "Mal Satış (Stok Çıkış)"])
        miktar = st.number_input("Miktar", min_value=0.01, step=0.1, format="%.2f")
        fiyat = st.number_input("Fiyat", min_value=0.0, step=0.1, format="%.2f")
        if st.form_submit_button("Kaydet"):
            db.islem_kaydet(tip, cari, urun, miktar, miktar*fiyat, f"{miktar} x {fiyat}")
            st.toast("Kayıt Başarılı!")
            st.rerun()

# 2. MODÜL: NAKİT
elif secenek == "Nakit İşlemi (Ödeme/Tahsilat)":
    st.sidebar.subheader("Kasa")
    with st.sidebar.form("kasa"):
        cari = akilli_secim("Cari", cari_listesi, "kasa_cari")
        tip = st.selectbox("Tür", ["Tedarikçiye Ödeme", "Müşteriden Tahsilat"])
        tutar = st.number_input("Tutar", min_value=0.0, step=0.1, format="%.2f")
        aciklama = st.text_input("Açıklama")
        if st.form_submit_button("Kaydet"):
            db.islem_kaydet(tip, cari, "-", 0, tutar, aciklama)
            st.toast("Finansal işlem tamam!")
            st.rerun()

# 3. MODÜL: KAVURMA
elif secenek == "🔥 Kavurma (Üretim)":
    st.sidebar.subheader("Kavurma")
    with st.sidebar.form("kavurma"):
        yesil = akilli_secim("Yeşil", urun_listesi, "giris")
        kg_gir = st.number_input("Yeşil (Kg)", min_value=0.1, format="%.2f")
        st.divider()
        kavruk = akilli_secim("Kavrulmuş", urun_listesi, "cikis")
        kg_cik = st.number_input("Kavrulmuş (Kg)", min_value=0.1, format="%.2f")
        if st.form_submit_button("🔥 Kaydet"):
            if kg_gir > kg_cik:
                fire = kg_gir - kg_cik
                db.islem_kaydet("Kavurma (Hammadde Çıkışı)", "Üretim", yesil, kg_gir, 0, f"Fire: {fire:.2f}")
                db.islem_kaydet("Kavurma (Ürün Girişi)", "Üretim", kavruk, kg_cik, 0, "Üretim")
                st.success("Üretim Kaydedildi!")
                st.rerun()

# 4. MODÜL: SİLME (YENİ!)
elif secenek == "🗑️ Kayıt Sil / Düzelt":
    st.sidebar.warning("⚠️ DİKKAT: Silinen veri geri gelmez!")
    if not df.empty:
        # Son 20 işlemi tersten gösterelim (En yeni en üstte)
        son_islemler = df.tail(20).iloc[::-1]
        
        # Seçim Kutusu için liste hazırlayalım
        # Format: "No: 5 | 2024-02-14 | Mal Alım | Ahmet..."
        islem_listesi = []
        for index, row in son_islemler.iterrows():
            bilgi = f"No:{index} | {row['Tarih']} | {row['İşlem Tipi']} | {row['Ürün']} | {row['Miktar']} br"
            islem_listesi.append((index, bilgi)) # (Gerçek Index, Görünen Yazı)
        
        secilen_islem = st.sidebar.selectbox("Silinecek İşlemi Seçin:", islem_listesi, format_func=lambda x: x[1])
        
        if st.sidebar.button("🗑️ SEÇİLİ KAYDI SİL"):
            secilen_index = secilen_islem[0] # Demetin ilk elemanı index
            db.kayit_sil(secilen_index)
            st.toast("Kayıt başarıyla silindi!")
            st.rerun()
    else:
        st.sidebar.info("Silinecek kayıt yok.")

# --- RAPORLAR ---
if not df.empty:
    t1, t2, t3 = st.tabs(["📦 Stok", "💰 Cari", "📜 Geçmiş"])
    with t1: st.dataframe(db.stok_durumu_hesapla(df), use_container_width=True)
    with t2:
        td, ms = db.cari_bakiye_hesapla(df)
        c1, c2 = st.columns(2)
        c1.dataframe(td, use_container_width=True); c2.dataframe(ms, use_container_width=True)
    with t3: st.dataframe(df.sort_index(ascending=False), use_container_width=True)
else:
    st.info("Kayıt bekleniyor...")