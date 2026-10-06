# Tugas 4 Praktikum Steganografi

Nama: Farid Firdaus  
NIM: 237006081  
Mata kuliah: Kriptografi

Implementasi dan bukti eksperimen Bagian II praktikum steganografi.

## Isi

- `cover_farid.png`: cover foto milik sendiri, PNG RGB 4032×3024.
- `src/praktikum_steganografi.py`: eksperimen P1–P5 dan bonus.
- `src/buat_laporan_praktikum.py`: pembuat laporan DOCX.
- `output/`: stego-image, change map, grafik PSNR, bidang LSB, dan hasil JSON.
- `screenshots/`: output console eksperimen.
- `237006081_Farid Firdaus_Praktikum.docx`: laporan Bagian II.

## Jalankan

```bash
python3 src/praktikum_steganografi.py
python3 src/buat_laporan_praktikum.py
```

Dependensi: Python 3, NumPy, Pillow, Matplotlib, python-docx.

## Ringkasan hasil

- P1: perbaikan 1-bit LSB memberi selisih maksimum 1 per channel-byte.
- P2: seed `237006081` berhasil; seed `237006082` gagal validasi header.
- P3: PSNR turun dari 51,14 dB (`m=1`) menjadi 31,81 dB (`m=4`).
- P4: plaintext pulih hanya jika key posisi dan key enkripsi benar.
- P5: PNG/BMP BER 0%; JPEG quality 95 BER 48,135965%.

Catatan: `output/p3` memakai payload 100% kapasitas dan tanpa header, khusus pengukuran MSE/PSNR.
