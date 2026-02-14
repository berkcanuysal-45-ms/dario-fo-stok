# db.py - SİLME ÖZELLİKLİ GÜNCEL VERSİYON
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import streamlit as st

# Google Sheets Bağlantısı
def baglanti_kur():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Stok Veritabanı").sheet1
    return sheet

# --- YARDIMCI DÖNÜŞTÜRÜCÜLER ---
def sayiya_cevir(deger):
    if pd.isna(deger) or str(deger).strip() == "": return 0.0
    deger = str(deger).strip()
    if isinstance(deger, (int, float)): return float(deger)
    if "." in deger and "," in deger: deger = deger.replace(".", "")
    deger = deger.replace(",", ".")
    try: return float(deger)
    except: return 0.0

def google_formatina_cevir(sayi):
    if sayi is None: return "0"
    return str(sayi).replace('.', ',')

# Verileri Çekme
def verileri_getir():
    sheet = baglanti_kur()
    try:
        raw_data = sheet.get_all_values()
        if not raw_data: return pd.DataFrame()
        basliklar = raw_data[0]
        veriler = raw_data[1:]
        df = pd.DataFrame(veriler, columns=basliklar)
        if not df.empty:
            for col in ['Miktar', 'Tutar']:
                if col in df.columns:
                    df[col] = df[col].apply(sayiya_cevir)
        return df
    except Exception as e:
        return pd.DataFrame()

# İşlem Kaydetme
def islem_kaydet(islem_tipi, cari, urun, miktar, tutar, aciklama):
    sheet = baglanti_kur()
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
    miktar_tr = google_formatina_cevir(miktar)
    tutar_tr = google_formatina_cevir(tutar)
    sheet.append_row([tarih, islem_tipi, cari, urun, miktar_tr, tutar_tr, aciklama], value_input_option='USER_ENTERED')

# --- YENİ EKLENEN FONKSİYON: KAYIT SİLME ---
def kayit_sil(pandas_index):
    sheet = baglanti_kur()
    # Google Sheet'te 1. satır başlıktır. Veriler 2. satırdan başlar.
    # Pandas index'i 0 olan veri, Sheet'te 2. satırdadır.
    # Formül: Pandas Index + 2 = Sheet Satır Numarası
    satir_numarasi = pandas_index + 2
    sheet.delete_rows(satir_numarasi)

# --- HESAPLAMALAR ---
def stok_durumu_hesapla(df):
    if df.empty: return pd.DataFrame()
    giris = df[df['İşlem Tipi'].isin(['Mal Alım (Stok Giriş)', 'Kavurma (Ürün Girişi)'])].groupby('Ürün')['Miktar'].sum()
    cikis = df[df['İşlem Tipi'].isin(['Mal Satış (Stok Çıkış)', 'Kavurma (Hammadde Çıkışı)'])].groupby('Ürün')['Miktar'].sum()
    stok = giris.subtract(cikis, fill_value=0).reset_index()
    stok.columns = ['Ürün Adı', 'Kalan Stok']
    stok = stok[stok['Kalan Stok'].abs() > 0.001]
    return stok

def cari_bakiye_hesapla(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    borc = df[df['İşlem Tipi'] == 'Mal Alım (Stok Giriş)'].groupby('Cari Adı')['Tutar'].sum()
    odenen = df[df['İşlem Tipi'] == 'Tedarikçiye Ödeme'].groupby('Cari Adı')['Tutar'].sum()
    alacak = df[df['İşlem Tipi'] == 'Mal Satış (Stok Çıkış)'].groupby('Cari Adı')['Tutar'].sum()
    tahsilat = df[df['İşlem Tipi'] == 'Müşteriden Tahsilat'].groupby('Cari Adı')['Tutar'].sum()
    return (borc.subtract(odenen, fill_value=0).reset_index(), alacak.subtract(tahsilat, fill_value=0).reset_index())