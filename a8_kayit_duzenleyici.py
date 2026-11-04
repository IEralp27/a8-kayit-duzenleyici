#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asphalt 8 Kayıt Düzenleyici (resmi olmayan)
===========================================

Asphalt 8: Airborne'un Windows sürümündeki yerel kayıt dosyasında
kredi ve token (mavi coin) önbelleği değerlerini değiştirir.

TEST EDİLEN SÜRÜM
  Asphalt 8: Airborne, Windows 10 (Microsoft Store / UWP, x86)
  Sürüm 3.7.0m  (paket sürümü 3.7.0.12)
  Başka sürümlerde dosya tanınmazsa program hiçbir şeyi değiştirmeden durur.

SORUMLULUK REDDİ
  * Bu proje bağımsız, resmi olmayan bir hobi/eğitim projesidir.
    Gameloft SE veya Microsoft ile hiçbir bağlantısı yoktur; bu şirketler
    tarafından onaylanmamış, desteklenmemiş veya sponsor olunmamıştır.
  * "Asphalt" ve "Asphalt 8: Airborne" Gameloft SE'nin ticari markalarıdır.
    Marka adı yalnızca uyumluluğu belirtmek için kullanılmıştır.
  * Bu yazılım oyuna ait hiçbir kod, dosya, görsel veya içerik barındırmaz
    ve dağıtmaz. Yalnızca kullanıcının kendi bilgisayarındaki, kendisine ait
    kayıt dosyası üzerinde çalışır.
  * Yalnızca kişisel, tek oyunculu ve çevrimdışı kullanım içindir.
    Çok oyunculu modlarda, çevrimiçi etkinliklerde veya başka oyunculara
    karşı haksız avantaj sağlamak amacıyla kullanılmamalıdır.
  * Kayıt dosyasını değiştirmek oyunun kullanım koşullarına aykırı olabilir
    ve hesabın askıya alınmasına/yasaklanmasına, ilerlemenin kaybına yol
    açabilir. Kullanıp kullanmamak ve tüm sonuçları tamamen kullanıcının
    kendi sorumluluğundadır.
  * Yazılım "OLDUĞU GİBİ" sunulur; çalışacağına, hatasız olduğuna veya
    belirli bir amaca uygun olduğuna dair açık ya da örtülü HİÇBİR GARANTİ
    verilmez. Yazar; veri kaybı, hesap yasağı veya başka herhangi bir
    doğrudan ya da dolaylı zarardan sorumlu tutulamaz.
  * Hak sahibi bir şirketin talebi halinde proje kaldırılacaktır.

DISCLAIMER (EN)
  Unofficial fan/educational project, not affiliated with or endorsed by
  Gameloft SE or Microsoft. "Asphalt" is a trademark of Gameloft SE.
  Contains no game code or assets; only edits the user's own local save file
  for personal, offline, single-player use. Modifying saves may violate the
  game's terms of service and lead to bans. Provided "AS IS", without
  warranty of any kind; the author accepts no liability for any damage.
  Use at your own risk.

LİSANS: MIT
  Bu yazılımın kopyası ücretsiz olarak herkese verilir; kullanma, kopyalama,
  değiştirme, birleştirme, yayımlama ve dağıtma serbesttir. Yukarıdaki telif
  bildirimi ve sorumluluk reddi tüm kopyalarda korunmalıdır. YAZILIM "OLDUĞU
  GİBİ", HİÇBİR GARANTİ OLMADAN SUNULUR; YAZAR HİÇBİR DURUMDA HERHANGİ BİR
  TALEP, ZARAR VEYA YÜKÜMLÜLÜKTEN SORUMLU DEĞİLDİR.

KULLANIM
    python a8_kayit_duzenleyici.py                 -> pencereli arayüz (çift tıklama da olur)
    python a8_kayit_duzenleyici.py --goster        -> mevcut değerleri göster
    python a8_kayit_duzenleyici.py --kredi 1000000 --token 5000
    python a8_kayit_duzenleyici.py --dosya "C:\\...\\LocalState\\profile" --kredi 500000
    python a8_kayit_duzenleyici.py --geri-yukle    -> en son yedeği geri koy

NOTLAR
  * Oyun TAMAMEN kapalıyken çalıştırın (açıkken kaydı sürekli yeniden yazar).
  * Her değişiklikten önce profile dosyasının zaman damgalı yedeği alınır.
  * Değerler 32 bitlik sayıdır; en fazla ~2 milyar olabilir.
  * Token değeri "önbellek" alanıdır; asıl bakiye sunucuda olabilir.
  * Değiştirilmiş kayıtla oyunu internete bağlamayın.

DOSYA BİÇİMİ (birlikte çalışabilirlik için incelenmiştir)
  profile dosyası aynı kaydın birkaç kopyasını içerir; her kopyanın CRC32
  değeri ve uzunluğu dosyada ayrıca saklanır. Kayıt: 0xED, u32 bayrak,
  u32 boyut1, u32 düz-boyut, ardından XTEA-ECB (32 tur) ile şifreli veri.
  XTEA anahtarı bir metnin 16 bayta XOR ile katlanmasıyla üretilir.
  Düz veri: u32 crc32(kalan), u32 öğe sayısı, sonra öğeler:
  u16 ad_uzunluğu, ad, u8 tür, u32 boyut, değer.
"""

import argparse
import datetime
import glob
import os
import shutil
import struct
import subprocess
import sys
import zlib

PAKET = "GAMELOFTSA.Asphalt8Airborne_0pp20fcewvvtj"
INT32_MAX = 2_147_483_647
PAY = 100_000_000  # kazanılan toplam kredi taşmasın diye bırakılan pay

ANAHTAR_METINLERI = [
    b"ERROR: cannot open stream '%s'",              # profile
    b"trying to map a file opened for writing !",   # settings
]

ALANLAR = {
    "kredi": "playerMoney",
    "kazanilan": "playerMoneyGained",
    "harcanan": "playerMoneySpent",
    "hosgeldin": "playerCreditsToCheckWelcomeGift",
    "token": "playerCachedHardCurrency",
}

# ---------------------------------------------------------------- XTEA
_M = 0xFFFFFFFF
_DELTA = 0x9E3779B9


def anahtar_uret(metin):
    kb = bytearray(16)
    for i, c in enumerate(metin):
        kb[i & 15] ^= c
    return struct.unpack("<4I", kb)


def _blok_coz(v0, v1, k):
    s = (_DELTA * 32) & _M
    for _ in range(32):
        v1 = (v1 - ((((v0 << 4) ^ (v0 >> 5)) + v0) ^ (s + k[(s >> 11) & 3]))) & _M
        s = (s - _DELTA) & _M
        v0 = (v0 - ((((v1 << 4) ^ (v1 >> 5)) + v1) ^ (s + k[s & 3]))) & _M
    return v0, v1


def _blok_sifrele(v0, v1, k):
    s = 0
    for _ in range(32):
        v0 = (v0 + ((((v1 << 4) ^ (v1 >> 5)) + v1) ^ (s + k[s & 3]))) & _M
        s = (s + _DELTA) & _M
        v1 = (v1 + ((((v0 << 4) ^ (v0 >> 5)) + v0) ^ (s + k[(s >> 11) & 3]))) & _M
    return v0, v1


def _ecb(veri, k, fn):
    out = bytearray()
    for i in range(0, len(veri) - len(veri) % 8, 8):
        a, b = struct.unpack("<2I", veri[i:i + 8])
        out += struct.pack("<2I", *fn(a, b, k))
    return bytes(out) + veri[len(veri) - len(veri) % 8:]


def coz(veri, k):
    return _ecb(veri, k, _blok_coz)


def sifrele(veri, k):
    return _ecb(veri, k, _blok_sifrele)


# ---------------------------------------------------------------- biçim
def _hepsini_bul(d, s):
    r, j = [], 0
    while True:
        j = d.find(s, j)
        if j < 0:
            return r
        r.append(j)
        j += 1


def _kopyalari_bul(ham):
    """Dosyadaki geçerli kayıt kopyalarını ve CRC/uzunluk etiketlerini bulur."""
    for p in _hepsini_bul(ham, b"\xed\x01\x00\x00\x00"):
        if p + 13 > len(ham):
            continue
        boyut1 = struct.unpack("<I", ham[p + 5:p + 9])[0]
        uzunluk = boyut1 + 9
        if uzunluk < 21 or p + uzunluk > len(ham):
            continue
        kayit = ham[p:p + uzunluk]
        etiket = struct.pack("<2I", zlib.crc32(kayit), uzunluk)
        etiketler = _hepsini_bul(ham, etiket)
        if not etiketler:
            continue
        kopyalar = [q for q in _hepsini_bul(ham, kayit)]
        return kayit, kopyalar, etiketler
    return None


def kaydi_ac(ham):
    bulunan = _kopyalari_bul(ham)
    if not bulunan:
        raise ValueError("Dosya tanınmadı (geçerli kayıt kopyası bulunamadı). "
                         "Farklı bir oyun sürümü olabilir ya da dosya bozuk.")
    kayit, kopyalar, etiketler = bulunan
    _bayrak, _b1, duz_boyut = struct.unpack("<3I", kayit[1:13])
    govde = kayit[13:]
    if duz_boyut > len(govde):
        raise ValueError("Kayıt başlığı beklenmedik.")
    for metin in ANAHTAR_METINLERI:
        k = anahtar_uret(metin)
        duz = coz(govde, k)
        if struct.unpack("<I", duz[:4])[0] == zlib.crc32(duz[4:duz_boyut]):
            return {"kopyalar": kopyalar, "etiketler": etiketler, "uzunluk": len(kayit),
                    "kayit": kayit, "govde": govde, "anahtar": k, "duz": duz,
                    "duz_boyut": duz_boyut}
    raise ValueError("Şifre çözülemedi: bu oyun sürümü farklı bir anahtar kullanıyor olabilir.")


def ogeler(duz, duz_boyut):
    adet = struct.unpack("<I", duz[4:8])[0]
    p, out = 8, {}
    for _ in range(adet):
        n = struct.unpack("<H", duz[p:p + 2])[0]
        ad = duz[p + 2:p + 2 + n].decode("latin1")
        p += 2 + n
        tur = duz[p]
        boyut = struct.unpack("<I", duz[p + 1:p + 5])[0]
        out[ad] = (tur, boyut, p + 5)
        p += 5 + boyut
        if p > duz_boyut:
            raise ValueError("Öğe listesi okunamadı.")
    return out


def kaydi_paketle(ham, bilgi, yeni_duz):
    duz = bytearray(yeni_duz)
    duz[0:4] = struct.pack("<I", zlib.crc32(bytes(duz[4:bilgi["duz_boyut"]])))
    yeni_govde = sifrele(bytes(duz), bilgi["anahtar"])
    kayit = bilgi["kayit"][:13] + yeni_govde
    assert len(kayit) == bilgi["uzunluk"]
    etiket = struct.pack("<2I", zlib.crc32(kayit), len(kayit))
    out = bytearray(ham)
    for i in bilgi["etiketler"]:
        out[i:i + 8] = etiket
    for j in bilgi["kopyalar"]:
        out[j:j + len(kayit)] = kayit
    return bytes(out)


# ---------------------------------------------------------------- yardımcılar
def varsayilan_yol():
    yerel = os.environ.get("LOCALAPPDATA")
    if not yerel:
        return None
    yol = os.path.join(yerel, "Packages", PAKET, "LocalState", "profile")
    return yol if os.path.exists(yol) else None


def oyun_acik_mi():
    if os.name != "nt":
        return False
    try:
        cikti = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Asphalt8.exe"],
                               capture_output=True, text=True, timeout=10).stdout
        return "Asphalt8.exe" in cikti
    except Exception:
        return False


def yedekle(yol):
    damga = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    hedef = yol + ".yedek_" + damga
    n = 1
    while os.path.exists(hedef):
        hedef = f"{yol}.yedek_{damga}_{n}"
        n += 1
    shutil.copy2(yol, hedef)
    return hedef


def int_oku(duz, ogeler_, ad):
    _t, _b, o = ogeler_[ad]
    return struct.unpack("<i", duz[o:o + 4])[0]


def int_yaz(duz, ogeler_, ad, deger):
    _t, _b, o = ogeler_[ad]
    duz[o:o + 4] = struct.pack("<i", deger)


def bicimle(n):
    return f"{n:,}".replace(",", ".")


def degerleri_oku(yol):
    """Kayıttaki para değerlerini sözlük olarak döndürür."""
    with open(yol, "rb") as f:
        bilgi = kaydi_ac(f.read())
    og = ogeler(bilgi["duz"], bilgi["duz_boyut"])
    sonuc = {}
    for anahtar, alan in ALANLAR.items():
        if alan in og:
            sonuc[anahtar] = int_oku(bilgi["duz"], og, alan)
    return sonuc


def degerleri_yazdir(d):
    print("  Kredi           :", bicimle(d["kredi"]))
    print("  Kazanılan toplam:", bicimle(d["kazanilan"]))
    print("  Harcanan toplam :", bicimle(d["harcanan"]))
    if "token" in d:
        print("  Token (önbellek):", bicimle(d["token"]))


def sinirla(deger, ad, uyarilar):
    if deger < 0:
        raise ValueError(f"{ad} negatif olamaz.")
    sinir = INT32_MAX - PAY
    if deger > sinir:
        uyarilar.append(f"{ad} en fazla {bicimle(sinir)} olabilir (32 bit sınırı); bu değere ayarlandı.")
        return sinir
    return deger


def duzenle(yol, kredi=None, token=None):
    """Değerleri değiştirir. (önceki, yeni, yedek_yolu, uyarılar) döndürür."""
    with open(yol, "rb") as f:
        ham = f.read()
    bilgi = kaydi_ac(ham)
    duz = bytearray(bilgi["duz"])
    og = ogeler(duz, bilgi["duz_boyut"])
    for gerekli in ("kredi", "kazanilan", "harcanan"):
        if ALANLAR[gerekli] not in og:
            raise ValueError(f"'{ALANLAR[gerekli]}' alanı kayıtta bulunamadı.")
    onceki = {a: int_oku(duz, og, f) for a, f in ALANLAR.items() if f in og}
    uyarilar = []

    if kredi is not None:
        kredi = sinirla(kredi, "Kredi", uyarilar)
        harcanan = int_oku(duz, og, ALANLAR["harcanan"])
        int_yaz(duz, og, ALANLAR["kredi"], kredi)
        # Oyun kredi = kazanılan - harcanan tutarlılığına bakıyor olabilir
        int_yaz(duz, og, ALANLAR["kazanilan"], kredi + harcanan)
        if ALANLAR["hosgeldin"] in og:
            int_yaz(duz, og, ALANLAR["hosgeldin"], kredi + harcanan)
    if token is not None:
        if ALANLAR["token"] not in og:
            uyarilar.append("Token alanı bu kayıtta yok, atlandı.")
        else:
            int_yaz(duz, og, ALANLAR["token"], sinirla(token, "Token", uyarilar))

    yeni = kaydi_paketle(ham, bilgi, bytes(duz))

    # Doğrulama: yeni dosyayı tekrar aç
    kontrol = kaydi_ac(yeni)
    og2 = ogeler(kontrol["duz"], kontrol["duz_boyut"])
    sonraki = {a: int_oku(kontrol["duz"], og2, f) for a, f in ALANLAR.items() if f in og2}

    yedek = yedekle(yol)
    with open(yol, "wb") as f:
        f.write(yeni)
    return onceki, sonraki, yedek, uyarilar


def geri_yukle(yol):
    yedekler = sorted(glob.glob(yol + ".yedek_*"))
    if not yedekler:
        return None
    son = yedekler[-1]
    shutil.copy2(son, yol)
    return son


# ---------------------------------------------------------------- arayüz
def arayuz(baslangic_yolu=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    ADIM = 1_000_000

    kok = tk.Tk()
    kok.title("Asphalt 8 Kayıt Düzenleyici")
    kok.resizable(False, False)

    yol_var = tk.StringVar(value=baslangic_yolu or "")
    kredi_var = tk.StringVar()
    token_var = tk.StringVar()
    mevcut_var = tk.StringVar(value="Kayıt dosyası seçilmedi.")

    def sayi(s):
        s = s.strip().replace(".", "").replace(",", "").replace(" ", "")
        if s.startswith("+"):
            s = s[1:]
        if s == "":
            return None
        if s.lstrip("-").isdigit():
            return int(s)
        raise ValueError(f"'{s}' geçerli bir sayı değil.")

    def yenile():
        yol = yol_var.get()
        if not yol or not os.path.exists(yol):
            mevcut_var.set("Kayıt dosyası bulunamadı. 'Dosya seç' ile profile dosyasını gösterin.")
            kaydet_btn.state(["disabled"])
            return
        try:
            d = degerleri_oku(yol)
        except Exception as e:
            mevcut_var.set(f"Dosya okunamadı: {e}")
            kaydet_btn.state(["disabled"])
            return
        satirlar = [f"Kredi: {bicimle(d['kredi'])}",
                    f"Kazanılan toplam: {bicimle(d['kazanilan'])}   Harcanan toplam: {bicimle(d['harcanan'])}"]
        if "token" in d:
            satirlar.insert(1, f"Token (önbellek): {bicimle(d['token'])}")
            token_var.set(bicimle(d["token"]))
            token_giris.state(["!disabled"])
        else:
            token_var.set("")
            token_giris.state(["disabled"])
        kredi_var.set(bicimle(d["kredi"]))
        mevcut_var.set("\n".join(satirlar))
        kaydet_btn.state(["!disabled"])

    def dosya_sec():
        bas = os.path.dirname(yol_var.get()) if yol_var.get() else None
        s = filedialog.askopenfilename(title="profile dosyasını seçin", initialdir=bas)
        if s:
            yol_var.set(s)
            yenile()

    def degistir(var, fark):
        try:
            v = sayi(var.get()) or 0
        except ValueError:
            v = 0
        var.set(bicimle(max(0, v + fark)))

    def kaydet():
        yol = yol_var.get()
        if oyun_acik_mi():
            messagebox.showwarning("Oyun açık", "Asphalt 8 açık görünüyor.\nOyunu tamamen kapatıp tekrar deneyin.")
            return
        try:
            kredi = sayi(kredi_var.get())
            token = sayi(token_var.get()) if "disabled" not in token_giris.state() else None
            onceki, sonraki, yedek, uyarilar = duzenle(yol, kredi, token)
        except Exception as e:
            messagebox.showerror("Hata", str(e))
            return
        mesaj = (f"Kredi: {bicimle(onceki['kredi'])} → {bicimle(sonraki['kredi'])}\n")
        if "token" in sonraki:
            mesaj += f"Token: {bicimle(onceki['token'])} → {bicimle(sonraki['token'])}\n"
        if uyarilar:
            mesaj += "\n" + "\n".join("• " + u for u in uyarilar) + "\n"
        mesaj += f"\nYedek alındı:\n{yedek}\n\nOyunu internetsiz açmanız önerilir."
        messagebox.showinfo("Kaydedildi", mesaj)
        yenile()

    def geri_al():
        if oyun_acik_mi():
            messagebox.showwarning("Oyun açık", "Önce oyunu kapatın.")
            return
        son = geri_yukle(yol_var.get())
        if son:
            messagebox.showinfo("Geri yüklendi", f"En son yedek geri yüklendi:\n{son}")
        else:
            messagebox.showinfo("Yedek yok", "Bu dosya için yedek bulunamadı.")
        yenile()

    cerceve = ttk.Frame(kok, padding=14)
    cerceve.grid()

    ttk.Label(cerceve, text="Kayıt dosyası (profile):").grid(row=0, column=0, columnspan=4, sticky="w")
    ttk.Entry(cerceve, textvariable=yol_var, width=62, state="readonly").grid(row=1, column=0, columnspan=3, sticky="we")
    ttk.Button(cerceve, text="Dosya seç", command=dosya_sec).grid(row=1, column=3, padx=(6, 0))

    ttk.Label(cerceve, textvariable=mevcut_var, foreground="#444", justify="left").grid(
        row=2, column=0, columnspan=4, sticky="w", pady=(10, 12))

    def satir(r, etiket, var):
        ttk.Label(cerceve, text=etiket).grid(row=r, column=0, sticky="w", pady=3)
        giris = ttk.Entry(cerceve, textvariable=var, width=22, justify="right")
        giris.grid(row=r, column=1, sticky="w")
        kutu = ttk.Frame(cerceve)
        kutu.grid(row=r, column=2, columnspan=2, sticky="w", padx=(6, 0))
        ttk.Button(kutu, text="− 1M", width=6, command=lambda: degistir(var, -ADIM)).grid(row=0, column=0)
        ttk.Button(kutu, text="+ 1M", width=6, command=lambda: degistir(var, ADIM)).grid(row=0, column=1, padx=3)
        ttk.Button(kutu, text="Max", width=6,
                   command=lambda: var.set(bicimle(INT32_MAX - PAY))).grid(row=0, column=2)
        return giris

    satir(3, "Yeni kredi:", kredi_var)
    token_giris = satir(4, "Yeni token:", token_var)

    ttk.Label(cerceve, text="İstediğiniz sayıyı yazabilir ya da butonlarla artırıp azaltabilirsiniz. "
                            f"En fazla {bicimle(INT32_MAX - PAY)}.",
              foreground="#666", wraplength=470).grid(row=5, column=0, columnspan=4, sticky="w", pady=(6, 10))

    butonlar = ttk.Frame(cerceve)
    butonlar.grid(row=6, column=0, columnspan=4, sticky="e")
    ttk.Button(butonlar, text="Yedeği geri yükle", command=geri_al).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(butonlar, text="Yenile", command=yenile).grid(row=0, column=1, padx=(0, 6))
    kaydet_btn = ttk.Button(butonlar, text="Kaydet", command=kaydet)
    kaydet_btn.grid(row=0, column=2)

    ttk.Label(cerceve, text="Oyun kapalıyken kullanın. Değiştirilmiş kayıtla internete bağlanmak ban riski taşır.",
              foreground="#a33", wraplength=470).grid(row=7, column=0, columnspan=4, sticky="w", pady=(12, 0))
    ttk.Label(cerceve, text="Resmi olmayan bir araçtır; Gameloft ile bağlantısı yoktur. Test edilen sürüm: "
                            "Asphalt 8 Windows 3.7.0m. Kullanım tamamen kullanıcının sorumluluğundadır; "
                            "yazılım garanti verilmeden sunulur.",
              foreground="#777", wraplength=470).grid(row=8, column=0, columnspan=4, sticky="w", pady=(6, 0))

    yenile()
    kok.mainloop()


def main():
    ap = argparse.ArgumentParser(description="Asphalt 8 (Windows) kayıt düzenleyici. "
                                             "Argümansız çalıştırılırsa pencere açılır.")
    ap.add_argument("--dosya", help="profile dosyasının yolu (varsayılan: otomatik bulunur)")
    ap.add_argument("--kredi", type=int, help="yeni kredi miktarı")
    ap.add_argument("--token", type=int, help="yeni token (mavi coin) miktarı")
    ap.add_argument("--goster", action="store_true", help="sadece mevcut değerleri göster")
    ap.add_argument("--geri-yukle", action="store_true", help="en son yedeği geri yükle")
    a = ap.parse_args()

    yol = a.dosya or varsayilan_yol()
    komut_satiri = a.goster or a.geri_yukle or a.kredi is not None or a.token is not None

    if not komut_satiri:
        try:
            arayuz(yol)
            return
        except ImportError:
            print("Pencere açılamadı (tkinter yok). Komut satırı seçeneklerini kullanın: --help")
            sys.exit(1)

    if not yol or not os.path.exists(yol):
        print("profile dosyası bulunamadı. --dosya ile yolunu verin.\n"
              f"Genelde: %LOCALAPPDATA%\\Packages\\{PAKET}\\LocalState\\profile")
        sys.exit(1)
    print(f"Kayıt dosyası: {yol}\n")

    try:
        if a.goster:
            degerleri_yazdir(degerleri_oku(yol))
            return
        if oyun_acik_mi():
            print("Asphalt 8 açık görünüyor. Lütfen oyunu tamamen kapatıp tekrar deneyin.")
            sys.exit(1)
        if a.geri_yukle:
            son = geri_yukle(yol)
            print(f"Geri yüklendi: {son}" if son else "Yedek bulunamadı.")
            return
        onceki, sonraki, yedek, uyarilar = duzenle(yol, a.kredi, a.token)
        print("Önceki değerler:")
        degerleri_yazdir(onceki)
        for u in uyarilar:
            print("  !", u)
        print("\nYeni değerler:")
        degerleri_yazdir(sonraki)
        print(f"\nKaydedildi. Yedek: {yedek}")
    except ValueError as e:
        print("HATA:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
