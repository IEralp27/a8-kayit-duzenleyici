#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Asphalt 8 kayıt dosyasındaki tüm alanları listeler (salt okunur, dosyayı değiştirmez).

Kullanım:
    python a8_dokum.py                 # varsayılan kayıt dosyası
    python a8_dokum.py "C:\\yol\\profile"
Çıktı: aynı klasöre a8_dokum.txt yazılır.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a8_kayit_duzenleyici import kaydi_ac, ogeler, varsayilan_yol  # noqa: E402


def onizle(tur, veri):
    if len(veri) == 4:
        i = struct.unpack("<i", veri)[0]
        f = struct.unpack("<f", veri)[0]
        return f"int={i}  float={f:.4g}"
    if len(veri) == 1:
        return f"byte={veri[0]}"
    if len(veri) == 8:
        return f"int64={struct.unpack('<q', veri)[0]}"
    yazi = "".join(chr(b) if 32 <= b < 127 else "." for b in veri[:80])
    return f"hex={veri[:32].hex()}  yazi={yazi}"


def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else varsayilan_yol()
    if not yol or not os.path.exists(yol):
        sys.exit("Kayıt dosyası bulunamadı. Yolu argüman olarak verin.")
    with open(yol, "rb") as f:
        ham = f.read()
    bilgi = kaydi_ac(ham)
    duz, boyut = bilgi["duz"], bilgi["duz_boyut"]
    alanlar = ogeler(duz, boyut)
    cikti = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a8_dokum.txt")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write(f"dosya={yol}  alan_sayisi={len(alanlar)}  duz_boyut={boyut}\n\n")
        for ad, (tur, b, o) in alanlar.items():
            f.write(f"{ad}\ttur={tur}\tboyut={b}\t{onizle(tur, duz[o:o + b])}\n")
    print(f"{len(alanlar)} alan yazıldı: {cikti}")


if __name__ == "__main__":
    main()
