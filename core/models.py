# core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser


# Model Pengguna yang bisa jadi Siswa atau Guru
class User(AbstractUser):
    ROLE_CHOICES = (
        ("Siswa", "Siswa"),
        ("Guru", "Guru"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=True, null=True)


# Model untuk Topik Utama (Bab)
class Topik(models.Model):
    judul = models.CharField(max_length=200)  # Contoh: "A. Ekosistem"
    urutan = models.IntegerField(default=0)

    class Meta:
        ordering = ["urutan"]

    def __str__(self):
        return self.judul


# Model untuk Sub-Topik (Materi di dalam Bab)
class SubTopik(models.Model):
    topik = models.ForeignKey(Topik, on_delete=models.CASCADE)
    judul = models.CharField(max_length=200)  # Contoh: "1. Jenis Ekosistem"
    konten = models.TextField(help_text="Isi konten utama untuk sub-topik ini.")
    urutan = models.IntegerField(default=0)
    pembuat = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={"role": "Guru"}
    )

    class Meta:
        ordering = ["topik__urutan", "urutan"]

    def __str__(self):
        return f"{self.topik.judul} -> {self.judul}"


# Model Kuis yang terhubung ke SubTopik
class Kuis(models.Model):
    subtopik = models.OneToOneField(SubTopik, on_delete=models.CASCADE)
    judul = models.CharField(max_length=200)

    def __str__(self):
        return self.judul


# Model Pertanyaan yang terhubung ke Kuis
class Pertanyaan(models.Model):
    kuis = models.ForeignKey(Kuis, on_delete=models.CASCADE, related_name="pertanyaan")
    teks_pertanyaan = models.CharField(max_length=255)

    def __str__(self):
        return self.teks_pertanyaan


# Model Pilihan Jawaban yang terhubung ke Pertanyaan
class PilihanJawaban(models.Model):
    pertanyaan = models.ForeignKey(
        Pertanyaan, on_delete=models.CASCADE, related_name="pilihan"
    )
    teks_jawaban = models.CharField(max_length=200)
    is_benar = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pertanyaan.teks_pertanyaan[:20]}... -> {self.teks_jawaban}"


# Tambahkan model-model ini di core/models.py


class Lencana(models.Model):
    nama = models.CharField(max_length=100)
    deskripsi = models.TextField()
    gambar_url = models.URLField(blank=True)  # URL ke gambar lencana
    syarat_poin = models.IntegerField(
        help_text="Poin minimum untuk mendapatkan lencana ini"
    )

    def __str__(self):
        return self.nama


class ProfilSiswa(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_poin = models.IntegerField(default=0)
    lencana = models.ManyToManyField(Lencana, blank=True)

    def __str__(self):
        return f"Profil {self.user.username}"


class PertanyaanArena(models.Model):
    TIPE_CHOICES = (
        ("klasifikasi", "Klasifikasi Komponen"),
        ("kartu_simbiosis", "Duel Simbiosis"),
        ("cerita_predator", "Jejak Predator"),
    )
    tipe = models.CharField(max_length=20, choices=TIPE_CHOICES)
    # Menyimpan data pertanyaan yang fleksibel dalam format JSON
    konten_json = models.JSONField()
    # Contoh: {'soal': 'Lebah dan Bunga', 'jawaban_benar': 'Mutualisme', 'pilihan': ['A', 'B', 'C']}

    def __str__(self):
        return f"{self.get_tipe_display()} - {self.id}"


class JawabanSiswa(models.Model):
    siswa = models.ForeignKey(User, on_delete=models.CASCADE)
    pertanyaan = models.ForeignKey(
        PertanyaanArena, on_delete=models.CASCADE, related_name="jawaban_siswa"
    )
    jawaban_benar = models.BooleanField()
    waktu_jawab = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Jawaban {self.siswa.username} untuk {self.pertanyaan.id}"


class HasilKuis(models.Model):
    siswa = models.ForeignKey(User, on_delete=models.CASCADE)
    kuis = models.ForeignKey(Kuis, on_delete=models.CASCADE)
    skor = models.FloatField()
    waktu_selesai = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Pastikan setiap siswa hanya punya satu entri hasil per kuis
        unique_together = ("siswa", "kuis")

    def __str__(self):
        return f"{self.siswa.username} - {self.kuis.judul}: {self.skor}%"
