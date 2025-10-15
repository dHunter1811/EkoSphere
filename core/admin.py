# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
# Import semua model Anda, termasuk HasilKuis
from .models import (User, Topik, SubTopik, Kuis, Pertanyaan, 
                     PilihanJawaban, Lencana, ProfilSiswa, 
                     PertanyaanArena, JawabanSiswa, HasilKuis) # <-- Tambahkan HasilKuis

# Kustomisasi tampilan admin untuk model User
class CustomUserAdmin(UserAdmin):
    fieldsets = list(UserAdmin.fieldsets)
    fieldsets[1] = ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'role')})

# Daftarkan User dengan kustomisasi baru
admin.site.register(User, CustomUserAdmin)

# Daftarkan model-model lainnya seperti biasa
admin.site.register(Topik)
admin.site.register(SubTopik)
admin.site.register(Kuis)
admin.site.register(Pertanyaan)
admin.site.register(PilihanJawaban)
admin.site.register(Lencana)
admin.site.register(ProfilSiswa)
admin.site.register(PertanyaanArena)
admin.site.register(JawabanSiswa)
admin.site.register(HasilKuis) # <-- TAMBAHKAN BARIS INI