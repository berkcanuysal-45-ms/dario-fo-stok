# main.py - HATA DÜZELTİLMİŞ VERSİYON
import streamlit as st
import db

st.set_page_config(page_title="Dario Fo Roastery", layout="wide")
st.title("☕ Dario Fo & Finora - Akıllı Stok")

# --- VERİTABANINDAN LİSTELERİ ÇEK ---
# Program her açıldığında mevcut isimleri öğrensin
df = db.verileri_getir()

mevcut_cariler = []
mevcut_urunler = []

if not df.empty:
    # HATA DÜZELTME: Sütun adlarını Google Sheet ile birebir aynı yaptık.
    # Tablonuzda "Cari Adı" ve "Ürün" yazıyor.
    
    if "Cari Adı" in df.columns:
        # Boş olmayan, benzersiz isimleri al
        mevcut_cariler = sorted([str(x) for x in df["Cari Adı"].unique() if str(x).strip() != "" and str(x) != "-"])
    
    if "Ürün" in df.columns:
        # Boş olmayan, benzersiz ürünleri al
        mevcut_urunler = sorted([str(x) for x in df["Ürün"].unique() if str(x).strip() != "" and str(x) != "-"])

# Listelerin başına "Yeni Ekle" seçeneği koyalım
cari_listesi = ["➕ YENİ CARİ EKLE..."] + mevcut_cariler
urun_listesi = ["➕ YENİ ÜRÜN EKLE..."] + mevcut_urunler

# --- YARDIMCI FONKSİYON: SEÇİM KUTUSU ---
def akilli_secim(etiket, liste, key_ozel):
    """
    Kullanıcıya önce listeyi gösterir, 'Yeni Ekle' derse yazı kutusu açar.
    """
    # Selectbox'a benzersiz key veriyoruz
    secim = st.selectbox(etiket, liste, key=f"sel_{key_ozel}")
    
    # Eğer kullanıcı "YENİ EKLE" seçerse veya liste boşsa ve sadece bu seçenek varsa
    if "YENİ" in str(secim):
        yeni_deger = st.text_input(f"Lütfen Yeni {etiket} Giriniz:", key=f"txt_{key_ozel}")
        return yeni_deger
    else:
        return secim

# --- YAN MENÜ ---
st.sidebar.header("📝 İşlem Seçimi")
secenek = st.sidebar.radio("Ne Yapacaksınız?", 
    ["Stok Hareketi (Alım/Satım)", "Nakit İşlemi (Ödeme/Tahsilat)", "🔥 Kavurma (Üretim)"])

# 1. MODÜL: STOK HAREKETİ
if secenek == "Stok Hareketi (Alım/Satım)":
    st.sidebar.subheader("Hızlı Alım/Satım")
    with st.sidebar.form("stok_form", clear_on_submit=True):
        
        cari = akilli_secim("Cari (Kişi/Firma)", cari_listesi, "stok_cari")
        urun = akilli_secim("Ürün", urun_listesi, "stok_urun")
        
        tip = st.selectbox("Yön", ["Mal Alım (Stok Giriş)", "Mal Satış (Stok Çıkış)"])
        miktar = st.number_input("Miktar (Kg/Adet)", min_value=0.01, step=0.1, format="%.2f")
        fiyat = st.number_input("Birim Fiyat", min_value=0.0, step=0.1, format="%.2f")
        
        btn = st.form_submit_button("Kaydet")
        
        if btn:
            if cari and urun:
                tutar = miktar * fiyat
                aciklama = f"{miktar} kg x {fiyat} TL"
                db.islem_kaydet(tip, cari, urun, miktar, tutar, aciklama)
                st.toast("✅ Kayıt Başarılı!")
                st.rerun()
            else:
                st.error("Lütfen isimleri boş bırakmayın.")

# 2. MODÜL: NAKİT İŞLEMİ
elif secenek == "Nakit İşlemi (Ödeme/Tahsilat)":
    st.sidebar.subheader("Kasa İşlemi")
    with st.sidebar.form("kasa_form", clear_on_submit=True):
        
        cari = akilli_secim("Cari (Kişi/Firma)", cari_listesi, "kasa_cari")
        
        tip = st.selectbox("Tür", ["Tedarikçiye Ödeme", "Müşteriden Tahsilat"])
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=0.1, format="%.2f")
        aciklama = st.text_input("Açıklama", placeholder="Havale, Nakit vb.")
        
        btn = st.form_submit_button("Kaydet")
        
        if btn:
            if cari:
                db.islem_kaydet(tip, cari, "-", 0, tutar, aciklama)
                st.toast("✅ Finansal işlem kaydedildi!")
                st.rerun()
            else:
                st.error("Lütfen cari seçin.")

# 3. MODÜL: KAVURMA (ÜRETİM)
elif secenek == "🔥 Kavurma (Üretim)":
    st.sidebar.subheader("Kavurma Verileri")
    with st.sidebar.form("kavurma_form", clear_on_submit=True):
        st.info("Yeşil düşer, Kavrulmuş eklenir.")
        
        st.markdown("**1. Hammadde (Giren Yeşil)**")
        # Buradaki key değerlerini değiştirdim ki çakışma olmasın
        yesil_urun = akilli_secim("Yeşil Çekirdek Seç", urun_listesi, "kavurma_giris_urunu")
        yesil_kg = st.number_input("Kullanılan Yeşil (Kg)", min_value=0.1, step=0.1, format="%.2f")
        
        st.divider()
        
        st.markdown("**2. Ürün (Çıkan Kahve)**")
        kavrulmus_urun = akilli_secim("Kavrulmuş Ürün Seç", urun_listesi, "kavurma_cikis_urunu")
        cikan_kg = st.number_input("Alınan Kavrulmuş (Kg)", min_value=0.1, step=0.1, format="%.2f")
        
        btn_kavur = st.form_submit_button("🔥 Kavur ve Kaydet")

        if btn_kavur:
            if yesil_kg > cikan_kg and yesil_urun and kavrulmus_urun:
                fire_kg = yesil_kg - cikan_kg
                fire_orani = (fire_kg / yesil_kg) * 100
                
                db.islem_kaydet("Kavurma (Hammadde Çıkışı)", "Dario Fo Üretim", yesil_urun, yesil_kg, 0, f"Fire: %{fire_orani:.1f}")
                db.islem_kaydet("Kavurma (Ürün Girişi)", "Dario Fo Üretim", kavrulmus_urun, cikan_kg, 0, f"Üretim. Kayıp: {fire_kg:.2f} kg")
                
                st.success(f"İşlem Tamam! Fire Oranı: %{fire_orani:.1f}")
                st.rerun()
            else:
                st.error("Eksik bilgi veya hatalı kilo girişi.")

# --- ANA EKRAN RAPORLAR ---
st.header("📊 Atölye Durumu")

if not df.empty:
    tab1, tab2, tab3 = st.tabs(["📦 Stoklar", "💰 Cari Hesaplar", "📜 Hareket Kayıtları"])
    
    with tab1:
        stok_df = db.stok_durumu_hesapla(df)
        st.dataframe(stok_df, use_container_width=True)
    
    with tab2:
        ted, mus = db.cari_bakiye_hesapla(df)
        c1, c2 = st.columns(2)
        c1.dataframe(ted, use_container_width=True)
        c2.dataframe(mus, use_container_width=True)
        
    with tab3:
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
else:
    st.info("Veri bekleniyor... Sol menüden ilk kaydınızı oluşturun.")