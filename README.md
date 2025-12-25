# 🔮 StatPub Checker - Publication Spell Checker & Converter App
**StatPub Checker** adalah aplikasi web berbasis Natural Language Processing (NLP) yang dirancang untuk membantu pemeriksaan kualitas penulisan pada naskah publikasi statistik, khususnya dalam mendeteksi kesalahan penulisan, inkonsistensi istilah, dan potensi typo pada dokumen DOCX/PDF.

Aplikasi ini mengombinasikan analisis linguistik otomatis dengan evaluasi pengguna (human-in-the-loop) untuk menghasilkan koreksi yang lebih akurat, kontekstual, dan sesuai dengan standar penulisan publikasi statistik.

> 🖥️ StatPub Checker dikembangkan sebagai alat bantu untuk meningkatkan kualitas publikasi statistik melalui pendekatan NLP yang praktis, transparan, dan berorientasi pada pengguna.

## 🚀 Try the App
Coba aplikasi web-nya disini:

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://statpub-checker.streamlit.app/)

## ✨ Features
- 📥 Upload & Pemeriksaan Dokumen DOCX/PDF
- 🎯 Deteksi Kesalahan Penulisan dan Rekomendasi Koreksi Otomatis
- 🖊️ Review & Seleksi Hasil Pemeriksaan oleh Pengguna
- 📃 Konversi Draft File dari Hasil Seleksi

## 🎥 Demo Video
Tonton video demonstrasinya disini:

## 🛠️ Tech Stack
- **Frontend:** Streamlit
- **Processing:** Python, pandas, python-docx, regex, SymSpell
- **NLP Resource:** KBBI, Kamus Indonesia & Inggris, Domain-specific vocabulary, Protected phrases & names

## 🚧 Status Proyek
Versi: 0.3.0
Status: Minimum Viable Product (MVP)

## 👤 Authors
Project ini dikembangkan oleh:
- Muhammad Ariq Hibatullah - S1 Sains Data
- Firdaini Azmi - S1 Sains Data

## 🆕 Update Log
### 🔸 v0.3.0 - 24 Desember 2025
- Menambahkan fitur highlight kata pada hasil konversi
- Menambahkan fitur preview dokumen untuk membantu proses review pengguna
- Mengoptimalkan sistem konversi dokumen

### 🔹 21 Desember 2025
- Manual Book penggunaan Aplikasi Web StatPub Checker v0.2 telah rilis!

### 🔸 v0.2.1 – 20 Desember 2025
- Menambahkan input Tipe publikasi untuk pengguna
- Menghapus input Threshold Confidence untuk pengguna
- Menambahkan sedikit penyesuaian pada program untuk developer

### 🔸 v0.2.0 – 18 Desember 2025
- Menambahkan fitur Review & Seleksi untuk mengoptimalkan output konfersi
- Update format file output untuk pengguna agar lebih memudahkan pembacaan

### 🔸 v0.1.0 – 17 Desember 2025
- Mengoptimalkan User Interface
- Mengubah bentuk output yang didapat oleh pengguna
