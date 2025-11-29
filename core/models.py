# core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from ckeditor.fields import RichTextField  # <-- Import ini tetap ada

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
    
    # =================================
    # PERBAIKAN: Kembalikan ke TextField
    # =================================
    konten = models.TextField(help_text="Isi konten utama untuk sub-topik ini.")
    # =================================
    
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
    
    # BIARKAN INI SEBAGAI RichTextField (SUDAH BENAR)
    penjelasan = RichTextField(
        blank=True, 
        null=True, 
        help_text="Penjelasan mengapa jawaban ini benar (opsional)."
    )

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
    
    # --- TAMBAHKAN FIELD INI ---
    total_waktu_akses = models.IntegerField(default=0, help_text="Total waktu akses dalam detik")

    def __str__(self):
        return f"Profil {self.user.username}"

    # --- TAMBAHKAN METODE INI ---
    def get_waktu_formatted(self):
        """Mengubah detik menjadi format Jam dan Menit"""
        jam = self.total_waktu_akses // 3600
        sisa_detik = self.total_waktu_akses % 3600
        menit = sisa_detik // 60
        
        if jam > 0:
            return f"{jam} Jam {menit} Menit"
        else:
            return f"{menit} Menit"


class PertanyaanArena(models.Model):
    TIPE_CHOICES = (
        ("klasifikasi", "Klasifikasi Komponen"),
        ("kartu_simbiosis", "Duel Simbiosis"),
        ("cerita_predator", "Jejak Predator"),
    )
    tipe = models.CharField(max_length=20, choices=TIPE_CHOICES)
    konten_json = models.JSONField()

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
        unique_together = ("siswa", "kuis")

    def __str__(self):
        return f"{self.siswa.username} - {self.kuis.judul}: {self.skor}%"
    
class InfoEkosistem(models.Model):
    KATEGORI_CHOICES = (
        ('Fauna', 'Fauna'),
        ('Flora', 'Flora'),
    )
    nama = models.CharField(max_length=100)
    deskripsi_singkat = models.TextField(max_length=200)
    gambar_url = models.URLField(max_length=500, help_text="URL gambar dari internet")
    kategori = models.CharField(max_length=10, choices=KATEGORI_CHOICES)

    class Meta:
        verbose_name = "Info Ekosistem"
        verbose_name_plural = "Info Ekosistem"

    def __str__(self):
        return self.nama


class UserMateriProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    materi = models.ForeignKey(SubTopik, on_delete=models.CASCADE) 
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'materi')

class QuizAttemptLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(Pertanyaan, on_delete=models.CASCADE) 
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question.teks_pertanyaan[:30]} - {self.is_correct}"