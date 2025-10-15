# core/urls.py

from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("register/", views.register_view, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="core/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page=reverse_lazy("login")),
        name="logout",
    ),
    # UBAH BARIS DI BAWAH INI
    path("materi/<int:pk>/", views.subtopik_detail_view, name="subtopik_detail"),
    path("materi/<int:pk>/kuis/", views.kuis_view, name="kuis"),
    # URL BARU UNTUK API GAME
    path("api/arena/klasifikasi/", views.api_klasifikasi_view, name="api_klasifikasi"),
    # URL BARU UNTUK API SIMULASI
    path(
        "api/simulasi/rantai-makanan/",
        views.api_rantai_makanan_view,
        name="api_rantai_makanan",
    ),
    # URL BARU UNTUK ARENA
    path("arena/duel-simbiosis/", views.duel_simbiosis_view, name="duel_simbiosis"),
    # URL BARU UNTUK MENYIMPAN JAWABAN ARENA
    path(
        "api/arena/simpan-jawaban/",
        views.api_simpan_jawaban_view,
        name="api_simpan_jawaban",
    ),
    # URL BARU UNTUK JEJAK PREDATOR
    path("arena/jejak-predator/", views.jejak_predator_view, name="jejak_predator"),
    # URL BARU UNTUK HALAMAN PROGRES SISWA
    path("progres/", views.progres_view, name="progres"),
]
