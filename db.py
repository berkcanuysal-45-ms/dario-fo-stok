# db.py - TÜRKÇE ONDALIK SORUNU İÇİN KESİN ÇÖZÜM
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import streamlit as st # Streamlit kütüphanesini ekledik

# Google Sheets Bağlantısı
def baglanti_kur():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # ÖNCE BULUTA BAK: Streamlit Secrets içinde anahtar var mı?
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    # YOKSA YERELE BAK: Bilgisayardaki dosyayı kullan
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        
    client = gspread.authorize(creds)
    sheet = client.open("Stok Veritabanı").sheet1
    return sheet

# --- OKUMA MOTORU (Google'dan Geleni Python'a Çevirir) ---
def sayiya_cevir(deger):
    """
    Google'dan gelen '43,50' (str) verisini -> 43.50 (float) yapar.
    """
    if pd.isna(deger) or str(deger).strip() == "":
        return 0.0
    
    deger = str(deger).strip()
    
    # Eğer zaten sayıysa (int/float) direkt döndür
    if isinstance(deger, (int, float)):
        return float(deger)
    
    # Binlik ayracı olan noktaları sil (1.250,50 -> 1250,50)
    if "." in deger and "," in deger:
        deger = deger.replace(".", "")
        
    # Virgülü noktaya çevir (43,50 -> 43.50)
    deger = deger.replace(",", ".")
    
    try:
        return float(deger)
    except:
        return 0.0

# --- YAZMA MOTORU (Python'dan Gideni Google'a Çevirir) ---
def google_formatina_cevir(sayi):
    """
    Python'daki 43.50 (float) sayısını -> '43,50' (str) yapar.
    Böylece Google Sheets onu doğru anlar.
    """
    if sayi is None:
        return "0"
    # Sayıyı önce string yap, sonra noktayı virgüle çevir
    return str(sayi).replace('.', ',')

# Verileri Çekme
def verileri_getir():
    sheet = baglanti_kur()
    try:
        raw_data = sheet.get_all_values()
        if not raw_data: 
            return pd.DataFrame()
            
        basliklar = raw_data[0]
        veriler = raw_data[1:]
        
        df = pd.DataFrame(veriler, columns=basliklar)
        
        if not df.empty:
            # Miktar ve Tutar sütunlarını temizle
            cols_to_fix = ['Miktar', 'Tutar']
            for col in cols_to_fix:
                if col in df.columns:
                    df[col] = df[col].apply(sayiya_cevir)
                    
        return df
    except Exception as e:
        print(f"Hata: {e}")
        return pd.DataFrame()

# İşlem Kaydetme
def islem_kaydet(islem_tipi, cari, urun, miktar, tutar, aciklama):
    sheet = baglanti_kur()
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # BURASI ÇOK ÖNEMLİ:
    # Veriyi gönderirken Python formatını (43.5) zorla TR formatına (43,5) çeviriyoruz.
    miktar_tr = google_formatina_cevir(miktar)
    tutar_tr = google_formatina_cevir(tutar)
    
    # value_input_option='USER_ENTERED' sayesinde sanki elle yazmışız gibi algılar
    sheet.append_row(
        [tarih, islem_tipi, cari, urun, miktar_tr, tutar_tr, aciklama],
        value_input_option='USER_ENTERED'
    )

# --- HESAPLAMALAR ---
def stok_durumu_hesapla(df):
    if df.empty: return pd.DataFrame()
    
    giris_tipleri = ['Mal Alım (Stok Giriş)', 'Kavurma (Ürün Girişi)']
    giris = df[df['İşlem Tipi'].isin(giris_tipleri)].groupby('Ürün')['Miktar'].sum()
    
    cikis_tipleri = ['Mal Satış (Stok Çıkış)', 'Kavurma (Hammadde Çıkışı)']
    cikis = df[df['İşlem Tipi'].isin(cikis_tipleri)].groupby('Ürün')['Miktar'].sum()
    
    stok = giris.subtract(cikis, fill_value=0).reset_index()
    stok.columns = ['Ürün Adı', 'Kalan Stok (Kg/Adet)']
    
    # 0.01'den küçük stokları gösterme (Küsürat temizliği)
    stok = stok[stok['Kalan Stok (Kg/Adet)'].abs() > 0.001]
    
    return stok

def cari_bakiye_hesapla(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    
    borc = df[df['İşlem Tipi'] == 'Mal Alım (Stok Giriş)'].groupby('Cari Adı')['Tutar'].sum()
    odenen = df[df['İşlem Tipi'] == 'Tedarikçiye Ödeme'].groupby('Cari Adı')['Tutar'].sum()
    
    alacak = df[df['İşlem Tipi'] == 'Mal Satış (Stok Çıkış)'].groupby('Cari Adı')['Tutar'].sum()
    tahsilat = df[df['İşlem Tipi'] == 'Müşteriden Tahsilat'].groupby('Cari Adı')['Tutar'].sum()

    tedarikci = borc.subtract(odenen, fill_value=0).reset_index()
    tedarikci.columns = ['Tedarikçi', 'Bakiye (Borcumuz)']
    
    musteri = alacak.subtract(tahsilat, fill_value=0).reset_index()
    musteri.columns = ['Müşteri', 'Bakiye (Alacağımız)']
    
    return tedarikci, musteri