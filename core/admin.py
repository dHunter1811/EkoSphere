# core/admin.py

from django.contrib import admin
from django.db import models
from django import forms  # <-- Pastikan ini diimpor
from .models import (
    User, Topik, SubTopik, Kuis, Pertanyaan, PilihanJawaban, 
    Lencana, ProfilSiswa, PertanyaanArena, JawabanSiswa, 
    HasilKuis, InfoEkosistem, UserMateriProgress, QuizAttemptLog
)

# --- 1. Buat Form kustom untuk SubTopik Admin ---
class SubTopikAdminForm(forms.ModelForm):
    class Meta:
        model = SubTopik
        fields = '__all__'
        widgets = {
            # Paksa 'konten' untuk menggunakan Textarea bawaan Django yang besar
            'konten': forms.Textarea(attrs={'rows': 40, 'cols': 100}),
        }

# --- 2. Gunakan form kustom di SubTopikAdmin ---
class SubTopikAdmin(admin.ModelAdmin):
    form = SubTopikAdminForm 

# --- 3. Daftarkan model Anda ---
admin.site.register(User)
admin.site.register(Topik)
admin.site.register(SubTopik, SubTopikAdmin) # <-- Ini sekarang menggunakan form kustom
admin.site.register(Kuis)
admin.site.register(Pertanyaan) # Pertanyaan akan tetap otomatis pakai CKEditor
admin.site.register(PilihanJawaban)
admin.site.register(Lencana)
admin.site.register(ProfilSiswa)
admin.site.register(PertanyaanArena)
admin.site.register(JawabanSiswa)
admin.site.register(HasilKuis)
admin.site.register(InfoEkosistem)
admin.site.register(UserMateriProgress)
admin.site.register(QuizAttemptLog)