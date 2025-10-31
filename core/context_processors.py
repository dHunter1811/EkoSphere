# core/context_processors.py

from .models import ProfilSiswa

def add_profil_to_context(request):
    """
    Fungsi ini akan otomatis menambahkan data profil siswa
    ke setiap halaman jika pengguna adalah seorang siswa.
    """
    if request.user.is_authenticated and request.user.role == 'Siswa':
        # Ambil atau buat profil untuk siswa yang sedang login
        profil, created = ProfilSiswa.objects.get_or_create(user=request.user)
        # Kirim data profil ke semua template
        return {'profil_siswa': profil}
    return {}