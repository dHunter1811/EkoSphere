# EkoSphere: Media Pembelajaran Ekosistem Interaktif

![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Completed-success?style=for-the-badge)

> **Media Pembelajaran Biologi Kelas X SMA Berbasis Web dengan Topik Ekosistem Lahan Basah.**

---

## Tentang Proyek

**EkoSphere** adalah platform pembelajaran berbasis web yang dirancang untuk mengatasi kejenuhan siswa terhadap materi modul statis (PDF). Proyek ini dikembangkan sebagai Laporan Akhir mata kuliah **Proyek Perangkat Lunak** di Universitas Lambung Mangkurat.

Sistem ini menerapkan konsep **Gamifikasi** dan **Micro-learning** untuk membuat materi "Interaksi Antar Komponen Ekosistem" menjadi lebih mudah dipahami dan menyenangkan. Fokus materi mengangkat kekayaan alam lokal **Lahan Basah (Wetlands)**.

### Fitur Utama

#### Untuk Siswa (Student)
* **Micro-learning Modules:** Materi dipecah menjadi bagian-bagian kecil (Sub-topik) agar mudah dicerna, dilengkapi *Uji Pemahaman Cepat*.
* **Zona Arena (Minigames):**
    * *Klasifikasi:* Memilah komponen Biotik vs Abiotik.
    * *Duel Simbiosis:* Tebak cepat hubungan antar makhluk hidup.
    * *Jejak Predator:* Analisis kasus rantai makanan.
    * *Energy Flow:* Menyusun rantai makanan.
* **Gamifikasi Penuh:** Sistem Poin, Lencana (Badges), dan Papan Peringkat (Leaderboard).

#### Untuk Guru (Teacher)
* **Teacher Dashboard:** Memantau progres kelas secara *real-time*.
* **Analitik Kesulitan:** Fitur "Peta Kesulitan Konsep" untuk melihat soal mana yang paling sering salah dijawab siswa.
* **Manajemen Siswa:** Melihat riwayat login, pengerjaan kuis, dan perolehan lencana.

---

## Teknologi yang Digunakan

Proyek ini dibangun menggunakan arsitektur **MVT (Model-View-Template)**:

* **Backend:** Django Framework (Python)
* **Database:** SQLite (Default Django DB)
* **Frontend:** HTML5, CSS3, JavaScript (AJAX/Fetch API untuk interaktivitas game tanpa reload)
* **Styling:** Custom CSS dengan desain *Card-Based Layout* dan palet warna alam (*Deep Forest Green*).

---

## Panduan Instalasi (Localhost)

Ikuti langkah-langkah berikut untuk menjalankan proyek di komputer lokal Anda:

1. **Clone Repository**
    ```bash
    git clone https://github.com/dHunter1811/EkoSphere.git
    cd EkoSphere
    ```

2. **Buat dan Aktifkan Virtual Environment**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Dependencies**
    ```bash
    pip install django django-ckeditor
    # Atau jika ada file requirements:
    pip install -r requirements.txt
    ```

4. **Migrasi Database**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5. **Buat Akun Superuser (Admin)**
    ```bash
    python manage.py createsuperuser
    ```

6. **Jalankan Server**
    ```bash
    python manage.py runserver
    ```
    Buka browser dan akses `http://127.0.0.1:8000/`.

---

## Panduan Penggunaan Singkat

### 1. Peran Siswa
* **Registrasi:** Buat akun baru sebagai "Siswa" pada halaman register.
* **Ekspedisi (Belajar):** Buka menu materi. Kerjakan *Uji Pemahaman Cepat* dan selesaikan **Kuis** dengan nilai minimal KKM (75) untuk membuka materi selanjutnya.
* **Arena:** Setelah materi selesai, akses menu **Zona Arena** untuk bermain game dan mendapatkan poin tambahan.
* **Profil:** Cek lencana yang berhasil didapatkan di menu Profil.

### 2. Peran Guru
* **Login:** Masuk menggunakan akun yang memiliki role "Guru".
* **Dashboard:** Lihat ringkasan "Siswa Perlu Perhatian" dan grafik performa kelas.
* **Laporan:** Klik "Laporan Kelas" untuk melihat detail mendalam per siswa.

### 3. Peran Admin
* Akses URL `/admin`.
* Login menggunakan akun Superuser.
* Kelola data master (User, Soal Kuis, Level Game, Topik Materi).

---

## Kontributor

Proyek ini dikembangkan oleh Tim Mahasiswa Pendidikan Komputer, Universitas Lambung Mangkurat:

| Nama | NIM | Peran | GitHub |
| :--- | :--- | :--- | :--- |
| **Muhammad Dimas Aditya** | 2310131210016 | **Fullstack Programmer** <br> (Back-End Logic, Database, API, Integration) | [@dHunter1811](https://github.com/dHunter1811) |
| **Muhammad Farros Shofiy** | 2310131310005 | **System Analyst & Content** <br> (Materi Biologi, UI/UX Design, Documentation) | [@KizuAnee](https://github.com/KizuAnee) |

---

<p align="center">
  Dibuat untuk Pendidikan Indonesia. <br>
  <b>© 2025 EkoSphere Team</b>
</p>


# EkoSphere Project
> _Software Project Development 2025_
