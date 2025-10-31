# core/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.utils.safestring import mark_safe
from .forms import CustomUserCreationForm
from django.contrib import messages  # <--- PASTIKAN INI ADA

# --- Model-model yang diimpor ---
from .models import (
    User,
    Topik,
    SubTopik,  # Ini adalah model 'Materi' Anda
    Kuis,
    Pertanyaan,  # Ini adalah model 'Question' Anda
    PilihanJawaban,  # Ditambahkan untuk kuis_view
    HasilKuis,
    ProfilSiswa,  # Ini adalah model 'Profile' Anda
    Lencana,
    PertanyaanArena,
    JawabanSiswa,
    InfoEkosistem,
    UserMateriProgress,
    QuizAttemptLog,
)


# --- Fungsi Helper Baru untuk Cek Guru ---
def is_guru(user):
    return user.is_authenticated and user.role == "Guru"


# --- Fungsi Helper Baru untuk Cek Siswa ---
def is_siswa(user):
    return user.is_authenticated and user.role == "Siswa"


# --- 1. FUNGSI DASHBOARD VIEW TELAH DIPERBAIKI ---
@login_required
def dashboard_view(request):

    # Logika "Pengatur Lalu Lintas"
    if request.user.role == "Guru":
        return redirect("teacher_dashboard")

    elif request.user.role == "Siswa":
        # Logika dashboard siswa (tidak berubah)
        profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
        hasil_kuis_siswa = HasilKuis.objects.filter(siswa=request.user)
        semua_subtopik = SubTopik.objects.all()
        completed_quiz_ids = set(hasil_kuis_siswa.values_list("kuis_id", flat=True))
        lencana_selanjutnya = (
            Lencana.objects.exclude(id__in=profil_siswa.lencana.all())
            .order_by("syarat_poin")
            .first()
        )
        progres_persen = 0
        if lencana_selanjutnya and lencana_selanjutnya.syarat_poin > 0:
            progres_persen = (
                profil_siswa.total_poin / lencana_selanjutnya.syarat_poin
            ) * 100
            if progres_persen > 100:
                progres_persen = 100
        info_items = InfoEkosistem.objects.order_by("?")[:3]
        context = {
            "daftar_materi": semua_subtopik,
            "profil_siswa": profil_siswa,
            "hasil_kuis_list": hasil_kuis_siswa,
            "completed_quiz_ids": completed_quiz_ids,
            "lencana_selanjutnya": lencana_selanjutnya,
            "progres_persen": progres_persen,
            "info_items": info_items,
        }
        return render(request, "core/dashboard.html", context)

    else:
        return redirect("login")


# --- 2. VIEW BARU: TEACHER DASHBOARD VIEW ---
@login_required
@user_passes_test(is_guru, login_url="/login/")
def teacher_dashboard_view(request):
    # Logika dashboard guru (tidak berubah)
    siswa_list = User.objects.filter(role="Siswa")
    total_siswa = siswa_list.count() if siswa_list.exists() else 1
    semua_materi = SubTopik.objects.all().order_by("topik__urutan", "urutan")
    progres_modul_kelas = []
    for materi in semua_materi:
        siswa_selesai_count = UserMateriProgress.objects.filter(materi=materi).count()
        persentase = (siswa_selesai_count / total_siswa) * 100
        progres_modul_kelas.append(
            {
                "nama_materi": materi.judul,
                "persentase": round(persentase),
                "label": f"{siswa_selesai_count} dari {total_siswa} siswa",
            }
        )
    siswa_berprestasi = ProfilSiswa.objects.filter(user__role="Siswa").order_by(
        "-total_poin"
    )[:3]
    siswa_perlu_perhatian = ProfilSiswa.objects.filter(
        user__role="Siswa", total_poin__lt=50
    ).order_by("total_poin")[:3]
    total_modul_selesai = UserMateriProgress.objects.count()
    total_modul_seharusnya = total_siswa * semua_materi.count()
    avg_completion_rate = (
        (total_modul_selesai / total_modul_seharusnya) * 100
        if total_modul_seharusnya > 0
        else 0
    )
    one_week_ago = timezone.now() - timezone.timedelta(days=7)
    siswa_aktif_count = siswa_list.filter(last_login__gte=one_week_ago).count()
    top_wrong_q_ids = (
        QuizAttemptLog.objects.filter(is_correct=False, user__role="Siswa")
        .values("question")
        .annotate(wrong_count=Count("question"))
        .order_by("-wrong_count")[:5]
    )
    peta_kesulitan = Pertanyaan.objects.filter(
        id__in=[item["question"] for item in top_wrong_q_ids]
    )
    context = {
        "progres_modul_kelas": progres_modul_kelas,
        "siswa_berprestasi": siswa_berprestasi,
        "siswa_perlu_perhatian": siswa_perlu_perhatian,
        "kpi_avg_completion": round(avg_completion_rate),
        "kpi_siswa_aktif": f"{siswa_aktif_count} dari {total_siswa} siswa",
        "peta_kesulitan": peta_kesulitan,
        "total_siswa": total_siswa,
        "daftar_materi": SubTopik.objects.filter(pembuat=request.user),
    }
    return render(request, "core/teacher_dashboard.html", context)


# --- 3. VIEW BARU: DETAIL SISWA VIEW ---
@login_required
@user_passes_test(is_guru, login_url="/login/")
def detail_siswa_view(request, user_id):
    # Logika detail siswa (tidak berubah)
    siswa = get_object_or_404(User, id=user_id, role="Siswa")
    profil_siswa = get_object_or_404(ProfilSiswa, user=siswa)
    hasil_kuis = HasilKuis.objects.filter(siswa=siswa).order_by("-waktu_selesai")
    semua_lencana = Lencana.objects.all().order_by("syarat_poin")
    lencana_dimiliki_ids = profil_siswa.lencana.values_list("id", flat=True)
    context = {
        "siswa": siswa,
        "profil_siswa": profil_siswa,
        "hasil_kuis_list": hasil_kuis,
        "semua_lencana": semua_lencana,
        "lencana_dimiliki_ids": lencana_dimiliki_ids,
    }
    return render(request, "core/progres.html", context)


# --- 4. VIEW SUBTOPIK DETAIL TELAH DIPERBARUI ---
@login_required
def subtopik_detail_view(request, pk):
    semua_topik = Topik.objects.all()
    subtopik_aktif = get_object_or_404(SubTopik, pk=pk)

    # --- LOGIKA UNTUK NAVIGASI ---
    semua_subtopik_terurut = list(
        SubTopik.objects.all().order_by("topik__urutan", "urutan")
    )  # Ditambahkan order_by
    try:
        current_index = semua_subtopik_terurut.index(subtopik_aktif)
        subtopik_sebelumnya = (
            semua_subtopik_terurut[current_index - 1] if current_index > 0 else None
        )
        subtopik_selanjutnya = (
            semua_subtopik_terurut[current_index + 1]
            if current_index < len(semua_subtopik_terurut) - 1
            else None
        )
    except ValueError:
        # Jika subtopik_aktif tidak ditemukan (seharusnya tidak terjadi dengan get_object_or_404)
        subtopik_sebelumnya = None
        subtopik_selanjutnya = None
    # --- AKHIR LOGIKA NAVIGASI ---

    # --- LOGIKA UNTUK PROGRES MISI (Kuis) ---
    topik_aktif = subtopik_aktif.topik
    total_subtopik_misi = topik_aktif.subtopik_set.count()
    kuis_selesai_count = 0
    if request.user.is_authenticated and request.user.role == "Siswa":
        kuis_selesai_count = HasilKuis.objects.filter(
            siswa=request.user, kuis__subtopik__topik=topik_aktif
        ).count()
    progres_misi_persen = 0
    if total_subtopik_misi > 0:
        progres_misi_persen = (kuis_selesai_count / total_subtopik_misi) * 100
    # --- AKHIR LOGIKA PROGRES MISI ---

    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)

    # --- LOGIKA BARU UNTUK TOMBOL & SIDEBAR ---
    completed_materi_ids = set()
    is_materi_selesai = False
    if request.user.is_authenticated and request.user.role == "Siswa":
        completed_materi_ids = set(
            UserMateriProgress.objects.filter(user=request.user).values_list(
                "materi_id", flat=True
            )
        )
        is_materi_selesai = subtopik_aktif.id in completed_materi_ids
    # --- AKHIR LOGIKA BARU ---

    context = {
        "semua_topik": semua_topik,
        "subtopik_aktif": subtopik_aktif,
        "subtopik_sebelumnya": subtopik_sebelumnya,
        "subtopik_selanjutnya": subtopik_selanjutnya,
        "progres_misi_persen": progres_misi_persen,
        "kuis_selesai_count": kuis_selesai_count,
        "total_subtopik_misi": total_subtopik_misi,
        # --- KIRIM DATA BARU KE TEMPLATE ---
        "completed_materi_ids": completed_materi_ids,
        "is_materi_selesai": is_materi_selesai,
    }
    return render(request, "core/materi_detail.html", context)


# --- SISA VIEWS ANDA (SUDAH DIPERBARUI & BENAR) ---


@login_required
@user_passes_test(is_siswa, login_url="/login/")
def kuis_view(request, pk):
    # Logika view kuis (tidak berubah)
    subtopik = get_object_or_404(SubTopik, pk=pk)
    kuis = subtopik.kuis
    if request.method == "POST":
        total_pertanyaan = kuis.pertanyaan.count()
        jawaban_benar = 0
        for pertanyaan in kuis.pertanyaan.all():
            jawaban_pengguna_id = request.POST.get(f"pertanyaan_{pertanyaan.id}")
            is_correct_answer = False
            if jawaban_pengguna_id:
                try:
                    pilihan_benar = pertanyaan.pilihan.get(is_benar=True)
                    if int(jawaban_pengguna_id) == pilihan_benar.id:
                        jawaban_benar += 1
                        is_correct_answer = True
                except PilihanJawaban.DoesNotExist:
                    pass
            QuizAttemptLog.objects.create(
                user=request.user, question=pertanyaan, is_correct=is_correct_answer
            )
        skor_saat_ini = (
            (jawaban_benar / total_pertanyaan) * 100 if total_pertanyaan > 0 else 0
        )
        profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
        try:
            hasil_sebelumnya = HasilKuis.objects.get(siswa=request.user, kuis=kuis)
            skor_sebelumnya = hasil_sebelumnya.skor
        except HasilKuis.DoesNotExist:
            skor_sebelumnya = 0.0
        HasilKuis.objects.update_or_create(
            siswa=request.user, kuis=kuis, defaults={"skor": skor_saat_ini}
        )
        tambahan_poin = 0
        if skor_saat_ini > skor_sebelumnya:
            jawaban_benar_sebelumnya = round((skor_sebelumnya / 100) * total_pertanyaan)
            selisih_jawaban_benar = jawaban_benar - jawaban_benar_sebelumnya
            tambahan_poin = selisih_jawaban_benar * 10
            if tambahan_poin > 0:
                profil_siswa.total_poin += tambahan_poin
                profil_siswa.save()
        lencana_baru_didapat = []
        lencana_yang_belum_dimiliki = Lencana.objects.exclude(profilsiswa=profil_siswa)
        for lencana in lencana_yang_belum_dimiliki:
            if profil_siswa.total_poin >= lencana.syarat_poin:
                profil_siswa.lencana.add(lencana)
                lencana_baru_didapat.append(lencana)
        context = {
            "skor": skor_saat_ini,
            "kuis": kuis,
            "lencana_baru": lencana_baru_didapat,
        }
        return render(request, "core/kuis_hasil.html", context)
    context = {"kuis": kuis}
    return render(request, "core/kuis.html", context)


def register_view(request):
    # Logika register (tidak berubah)
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = CustomUserCreationForm()
    context = {"form": form}
    return render(request, "core/register.html", context)


# --- SISA API & ARENA VIEWS (TIDAK BERUBAH) ---
def api_klasifikasi_view(request):
    pertanyaan = PertanyaanArena.objects.filter(tipe="klasifikasi").first()
    if pertanyaan:
        return JsonResponse(pertanyaan.konten_json)
    return JsonResponse({"error": "Data tidak ditemukan"}, status=404)


def api_rantai_makanan_view(request):
    data_ekosistem = {"nama": "Rawa Gambut", "organisme": [...]}  # Data statis
    return JsonResponse(data_ekosistem)


@login_required
@user_passes_test(is_siswa, login_url="/login/")
def duel_simbiosis_view(request):
    # Logika duel simbiosis (tidak berubah)
    pertanyaan_list = PertanyaanArena.objects.filter(tipe="kartu_simbiosis")
    data_untuk_js = []
    for p in pertanyaan_list:
        konten = p.konten_json
        konten["id"] = p.id
        data_untuk_js.append(konten)
    pertanyaan_json = mark_safe(json.dumps(data_untuk_js))
    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
    context = {"pertanyaan_json": pertanyaan_json, "profil_siswa": profil_siswa}
    return render(request, "core/arena_duel_simbiosis.html", context)


@login_required
@require_POST
@user_passes_test(is_siswa, login_url="/login/")
def api_simpan_jawaban_view(request):
    # Logika simpan jawaban arena (tidak berubah)
    data = json.loads(request.body)
    pertanyaan_id = data.get("pertanyaan_id")
    jawaban_benar = data.get("jawaban_benar")
    try:
        pertanyaan = PertanyaanArena.objects.get(id=pertanyaan_id)
        profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
        JawabanSiswa.objects.create(
            siswa=request.user, pertanyaan=pertanyaan, jawaban_benar=jawaban_benar
        )
        if jawaban_benar:
            profil_siswa.total_poin += 10
            profil_siswa.save()
        return JsonResponse(
            {"status": "sukses", "total_poin_baru": profil_siswa.total_poin}
        )
    except PertanyaanArena.DoesNotExist:
        return JsonResponse(
            {"status": "gagal", "error": "Pertanyaan tidak ditemukan"}, status=404
        )


@login_required
@user_passes_test(is_siswa, login_url="/login/")
def jejak_predator_view(request):
    # Logika jejak predator (tidak berubah)
    cerita = PertanyaanArena.objects.filter(tipe="cerita_predator").first()
    cerita_json = mark_safe(json.dumps(cerita.konten_json)) if cerita else None
    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
    context = {
        "cerita_json": cerita_json,
        "pertanyaan_id": cerita.id if cerita else None,
        "profil_siswa": profil_siswa,
    }
    return render(request, "core/arena_jejak_predator.html", context)


@login_required
@user_passes_test(is_siswa, login_url="/login/")
def progres_view(request):
    # Logika progres siswa (tidak berubah)
    profil_siswa = get_object_or_404(ProfilSiswa, user=request.user)
    hasil_kuis = HasilKuis.objects.filter(siswa=request.user).order_by("-waktu_selesai")
    semua_lencana = Lencana.objects.all().order_by("syarat_poin")
    lencana_dimiliki_ids = profil_siswa.lencana.values_list("id", flat=True)
    context = {
        "profil_siswa": profil_siswa,
        "hasil_kuis_list": hasil_kuis,
        "semua_lencana": semua_lencana,
        "lencana_dimiliki_ids": lencana_dimiliki_ids,
        "siswa": request.user,
    }
    return render(request, "core/progres.html", context)


# --- VIEW TANDAI SELESAI (SUDAH BENAR) ---
@login_required
@user_passes_test(is_siswa, login_url="/login/")
def tandai_materi_selesai_view(request, pk):
    materi = get_object_or_404(SubTopik, pk=pk)
    UserMateriProgress.objects.get_or_create(user=request.user, materi=materi)
    messages.success(request, f"Materi '{materi.judul}' telah ditandai selesai!")
    return redirect("subtopik_detail", pk=pk)


# --- VIEW BARU DITAMBAHKAN DI SINI ---
@login_required
@user_passes_test(is_siswa, login_url="/login/")
def batalkan_materi_selesai_view(request, pk):
    materi = get_object_or_404(SubTopik, pk=pk)
    progress_entry = UserMateriProgress.objects.filter(user=request.user, materi=materi)
    if progress_entry.exists():
        progress_entry.delete()
        messages.info(
            request, f"Materi '{materi.judul}' ditandai sebagai 'Belum Selesai'."
        )
    return redirect("subtopik_detail", pk=pk)
