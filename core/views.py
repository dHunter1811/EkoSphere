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


# Di dalam core/views.py

@login_required
def dashboard_view(request):

    if request.user.role == "Guru":
        return redirect("teacher_dashboard")

    elif request.user.role == "Siswa":
        profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
        hasil_kuis_siswa = HasilKuis.objects.filter(siswa=request.user).order_by('kuis__subtopik__urutan')
        
        semua_subtopik = SubTopik.objects.all().order_by('topik__urutan', 'urutan')
        
        # 1. Materi yang sudah selesai (Completed IDs)
        # Kita asumsikan 'Selesai' berarti sudah ditandai selesai (UserMateriProgress)
        # Jika Anda ingin syaratnya LULUS KUIS, ganti logikanya seperti subtopik_detail_view
        completed_materi_ids = set(
            UserMateriProgress.objects.filter(user=request.user).values_list('materi_id', flat=True)
        )
        
        # --- LOGIKA PENGUNCIAN ARENA ---
        # Kita cari ID materi prasyarat
        materi1_1 = semua_subtopik.filter(judul__icontains="1.1").first()
        materi1_2 = semua_subtopik.filter(judul__icontains="1.2").first()
        materi1_3 = semua_subtopik.filter(judul__icontains="1.3").first()
        
        arena_status = {
            "klasifikasi": {
                "locked": materi1_1.id not in completed_materi_ids if materi1_1 else True,
                "materi_pk": materi1_1.pk if materi1_1 else None,
                "materi_judul": materi1_1.judul if materi1_1 else "Materi 1.1"
            },
            "interaksi": { # Untuk Simbiosis & Predator
                "locked": materi1_2.id not in completed_materi_ids if materi1_2 else True,
                "materi_pk": materi1_2.pk if materi1_2 else None,
                "materi_judul": materi1_2.judul if materi1_2 else "Materi 1.2"
            },
            "energi": { # Untuk Energy Flow
                "locked": materi1_3.id not in completed_materi_ids if materi1_3 else True,
                "materi_pk": materi1_3.pk if materi1_3 else None,
                "materi_judul": materi1_3.judul if materi1_3 else "Materi 1.3"
            }
        }
        # -------------------------------

        # ... (Logika First Unlocked & Lencana TETAP SAMA) ...
        read_materi_ids = set(UserMateriProgress.objects.filter(user=request.user).values_list('materi_id', flat=True))
        passed_quiz_subtopik_ids = set(HasilKuis.objects.filter(siswa=request.user, skor__gte=75).values_list('kuis__subtopik_id', flat=True))
        
        first_unlocked_pk = None
        completed_materi_ids_display = set() # Untuk centang hijau di peta

        for subtopik in semua_subtopik:
            is_read = subtopik.id in read_materi_ids
            has_quiz = hasattr(subtopik, 'kuis')
            is_passed = subtopik.id in passed_quiz_subtopik_ids if has_quiz else True
            
            if is_read and is_passed:
                completed_materi_ids_display.add(subtopik.id)
            else:
                first_unlocked_pk = subtopik.pk
                break
        
        if first_unlocked_pk is None and semua_subtopik.exists():
            first_unlocked_pk = semua_subtopik.last().pk
            
        total_materi_count = semua_subtopik.count()
        semua_materi_selesai = (len(completed_materi_ids_display) == total_materi_count)

        lencana_selanjutnya = (
            Lencana.objects.exclude(id__in=profil_siswa.lencana.all())
            .order_by("syarat_poin")
            .first()
        )
        progres_persen = 0
        if lencana_selanjutnya and lencana_selanjutnya.syarat_poin > 0:
            progres_persen = (profil_siswa.total_poin / lencana_selanjutnya.syarat_poin) * 100
            if progres_persen > 100: progres_persen = 100
        
        info_items = InfoEkosistem.objects.order_by("?")[:6]
        siswa_teratas = ProfilSiswa.objects.filter(user__role="Siswa").order_by('-total_poin')[:3]

        context = {
            "profil_siswa": profil_siswa,
            "hasil_kuis_list": hasil_kuis_siswa,
            "lencana_selanjutnya": lencana_selanjutnya,
            "progres_persen": progres_persen,
            "info_items": info_items,
            "daftar_materi": semua_subtopik, 
            "completed_materi_ids": completed_materi_ids_display,
            "first_unlocked_pk": first_unlocked_pk,
            "semua_materi_selesai": semua_materi_selesai,
            "siswa_teratas": siswa_teratas,
            
            # Data Kunci Arena
            "arena_status": arena_status, 
        }
        return render(request, "core/dashboard.html", context)

    else:
        return redirect("login")


# --- 2. VIEW BARU: TEACHER DASHBOARD VIEW ---
@login_required
@user_passes_test(is_guru, login_url="/login/")  # Penjaga ini sudah benar
def teacher_dashboard_view(request):

    siswa_list = User.objects.filter(role="Siswa")
    total_siswa = siswa_list.count() if siswa_list.exists() else 1

    # --- 1. Progres Modul Kelas (Sudah Benar) ---
    semua_materi = SubTopik.objects.all().order_by("topik__urutan", "urutan")
    progres_modul_kelas = []
    for materi in semua_materi:
        siswa_selesai_count = UserMateriProgress.objects.filter(
            materi=materi, user__role="Siswa"
        ).count()
        persentase = (siswa_selesai_count / total_siswa) * 100
        progres_modul_kelas.append(
            {
                "nama_materi": materi.judul,
                "persentase": round(persentase),
                "label": f"{siswa_selesai_count} dari {total_siswa} siswa",
            }
        )

    # --- 2. Identifikasi Siswa (Sudah Benar) ---
    siswa_berprestasi = ProfilSiswa.objects.filter(
        user__role="Siswa", total_poin__gt=0
    ).order_by("-total_poin")[:3]

    siswa_perlu_perhatian = ProfilSiswa.objects.filter(
        user__role="Siswa", total_poin__lt=50
    ).order_by("total_poin")[:3]

    # --- 3. Statistik Kinerja Kelas (KPI) (Sudah Benar) ---
    total_modul_selesai = UserMateriProgress.objects.filter(user__role="Siswa").count()
    total_modul_seharusnya = total_siswa * semua_materi.count()
    avg_completion_rate = (
        (total_modul_selesai / total_modul_seharusnya) * 100
        if total_modul_seharusnya > 0
        else 0
    )

    one_week_ago = timezone.now() - timezone.timedelta(days=7)
    siswa_aktif_count = siswa_list.filter(last_login__gte=one_week_ago).count()

    # --- 4. Peta Kesulitan Konsep (LOGIKA DIPERBARUI & DIPERBAIKI) ---
    
    # Query dibungkus dengan () agar lebih aman dari error indentasi
    peta_kesulitan_data = (
        QuizAttemptLog.objects.filter(user__role="Siswa")
        .values("question")
        .annotate(
            total_attempts=Count("question"),  # Total pengerjaan
            wrong_count=Count("question", filter=Q(is_correct=False)), # Jumlah salah
        )
        .filter(wrong_count__gt=0)
        .order_by("-wrong_count")[:5]
    )
    
    peta_kesulitan = []
    for item in peta_kesulitan_data:
        question = Pertanyaan.objects.get(id=item["question"])
        wrong_count = item["wrong_count"]
        total_attempts = item["total_attempts"]
        
        # Hitung persentase kesalahan
        persentase_salah = (wrong_count / total_attempts) * 100 if total_attempts > 0 else 0
        
        peta_kesulitan.append({
            "teks_pertanyaan": question.teks_pertanyaan,
            "wrong_count": wrong_count,
            "persentase_salah": round(persentase_salah, 1),
        })
    # --- AKHIR LOGIKA BARU Peta Kesulitan Konsep ---


    # --- 5. LOGIKA BARU: Daftar Siswa Lengkap (Student Roster) ---
    daftar_siswa_lengkap = ProfilSiswa.objects.filter(user__role="Siswa").order_by(
        "user__username"
    )

    # --- 6. LOGIKA BARU: Analitik Rata-rata per Kuis ---
    semua_kuis = Kuis.objects.all().order_by("subtopik__urutan")
    analitik_kuis = []
    for kuis in semua_kuis:
        data = HasilKuis.objects.filter(kuis=kuis).aggregate(
            rata_rata_skor=Avg("skor"), jumlah_pengerjaan=Count("id")
        )
        rata_rata = data.get("rata_rata_skor")
        jumlah = data.get("jumlah_pengerjaan")

        analitik_kuis.append(
            {
                "judul_kuis": kuis.judul,
                "rata_rata": round(rata_rata) if rata_rata is not None else None,
                "jumlah_pengerjaan": jumlah,
            }
        )
    # --- AKHIR LOGIKA BARU ---

    context = {
        "progres_modul_kelas": progres_modul_kelas,
        "siswa_berprestasi": siswa_berprestasi,
        "siswa_perlu_perhatian": siswa_perlu_perhatian,
        "kpi_avg_completion": round(avg_completion_rate),
        "kpi_siswa_aktif": f"{siswa_aktif_count} dari {total_siswa} siswa",
        "peta_kesulitan": peta_kesulitan, # <-- Variabel ini sekarang berisi data baru
        "total_siswa": total_siswa,
        "daftar_siswa_lengkap": daftar_siswa_lengkap,
        "analitik_kuis": analitik_kuis,
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


@login_required
def subtopik_detail_view(request, pk):
    semua_topik = Topik.objects.all()
    subtopik_aktif = get_object_or_404(SubTopik, pk=pk)

    # --- LOGIKA NAVIGASI & PENGUNCIAN (DIPERBARUI) ---
    semua_subtopik_terurut = list(
        SubTopik.objects.all().order_by("topik__urutan", "urutan")
    )
    
    # 1. Tentukan Navigasi Prev/Next
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
        subtopik_sebelumnya = None
        subtopik_selanjutnya = None

    # 2. Ambil Progres Materi (Completed)
    completed_materi_ids = set()
    if request.user.is_authenticated and request.user.role == "Siswa":
        completed_materi_ids = set(
            UserMateriProgress.objects.filter(user=request.user).values_list(
                "materi_id", flat=True
            )
        )

    # 3. Hitung Materi yang 'Accessible' (Terbuka)
    # Logika: Materi pertama selalu terbuka. Materi ke-N terbuka jika materi ke-(N-1) selesai.
    accessible_ids = set()
    if semua_subtopik_terurut:
        # Materi pertama selalu terbuka
        accessible_ids.add(semua_subtopik_terurut[0].id)
        
        for i in range(len(semua_subtopik_terurut) - 1):
            current_sub = semua_subtopik_terurut[i]
            next_sub = semua_subtopik_terurut[i+1]
            
            # Jika materi saat ini sudah selesai, materi berikutnya terbuka
            if current_sub.id in completed_materi_ids:
                accessible_ids.add(next_sub.id)
            
            # Materi yang sudah selesai pasti accessible
            if current_sub.id in completed_materi_ids:
                accessible_ids.add(current_sub.id)
    # --- AKHIR LOGIKA BARU ---

    # --- LOGIKA KUIS & SIDEBAR ---
    topik_aktif = subtopik_aktif.topik
    total_subtopik_misi = topik_aktif.subtopik_set.count()
    kuis_selesai_list = [] 
    kuis_selesai_count = 0
    skor_tertinggi = 0
    passed_kkm = False

    if request.user.is_authenticated and request.user.role == "Siswa":
        hasil_kuis_topik = HasilKuis.objects.filter(
            siswa=request.user, kuis__subtopik__topik=topik_aktif
        ).select_related('kuis')
        kuis_selesai_count = hasil_kuis_topik.count()
        kuis_selesai_list = hasil_kuis_topik

        if hasattr(subtopik_aktif, 'kuis'):
            try:
                hasil_ini = HasilKuis.objects.get(siswa=request.user, kuis=subtopik_aktif.kuis)
                skor_tertinggi = hasil_ini.skor
                if skor_tertinggi >= 75:
                    passed_kkm = True
            except HasilKuis.DoesNotExist:
                skor_tertinggi = 0
        else:
            passed_kkm = True

    progres_misi_persen = 0
    if total_subtopik_misi > 0:
        progres_misi_persen = (kuis_selesai_count / total_subtopik_misi) * 100

    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
    is_materi_selesai = subtopik_aktif.id in completed_materi_ids
    can_proceed = is_materi_selesai and passed_kkm

    context = {
        "semua_topik": semua_topik,
        "subtopik_aktif": subtopik_aktif,
        "subtopik_sebelumnya": subtopik_sebelumnya,
        "subtopik_selanjutnya": subtopik_selanjutnya,
        "progres_misi_persen": progres_misi_persen,
        "kuis_selesai_count": kuis_selesai_count,
        "total_subtopik_misi": total_subtopik_misi,
        "completed_materi_ids": completed_materi_ids,
        "is_materi_selesai": is_materi_selesai,
        "kuis_selesai_list": kuis_selesai_list,
        "passed_kkm": passed_kkm,
        "skor_tertinggi": skor_tertinggi,
        "can_proceed": can_proceed,
        
        # KIRIM DATA INI KE TEMPLATE
        "accessible_ids": accessible_ids, 
    }
    return render(request, "core/materi_detail.html", context)

# --- 5. FUNGSI KUIS_VIEW TELAH DIPERBARUI ---
@login_required
@user_passes_test(is_siswa, login_url="/login/")
def kuis_view(request, pk):
    subtopik = get_object_or_404(SubTopik, pk=pk)
    kuis = subtopik.kuis

    if request.method == "POST":
        total_pertanyaan = kuis.pertanyaan.count()
        jawaban_benar = 0
        
        # --- LOGIKA BARU UNTUK REVIEW ---
        hasil_review = []
        semua_pertanyaan = kuis.pertanyaan.all()
        # --- AKHIR LOGIKA BARU ---
        
        for pertanyaan in semua_pertanyaan:
            jawaban_pengguna_id = request.POST.get(f"pertanyaan_{pertanyaan.id}")
            is_correct_answer = False
            pilihan_pengguna = None
            pilihan_benar = None

            try:
                # Ambil jawaban benar dari database
                pilihan_benar = pertanyaan.pilihan.get(is_benar=True)
            except PilihanJawaban.DoesNotExist:
                continue # Lompati soal ini jika tidak ada jawaban benar

            if jawaban_pengguna_id:
                try:
                    # Ambil pilihan jawaban pengguna
                    pilihan_pengguna = PilihanJawaban.objects.get(id=jawaban_pengguna_id)
                    if pilihan_pengguna == pilihan_benar:
                        jawaban_benar += 1
                        is_correct_answer = True
                except PilihanJawaban.DoesNotExist:
                    pass # Pilihan tidak valid

            # Simpan ke log (kode Anda yang sudah ada)
            QuizAttemptLog.objects.create(
                user=request.user, question=pertanyaan, is_correct=is_correct_answer
            )
            
            # --- TAMBAHKAN DATA KE LIST REVIEW ---
            hasil_review.append({
                'pertanyaan': pertanyaan,
                'pilihan_pengguna': pilihan_pengguna,
                'pilihan_benar': pilihan_benar,
                'is_correct': is_correct_answer
            })
            # --- AKHIR TAMBAHAN ---

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

        # ... (Logika penambahan poin Anda tetap sama) ...
        tambahan_poin = 0
        if skor_saat_ini > skor_sebelumnya:
            jawaban_benar_sebelumnya = round((skor_sebelumnya / 100) * total_pertanyaan)
            selisih_jawaban_benar = jawaban_benar - jawaban_benar_sebelumnya
            tambahan_poin = selisih_jawaban_benar * 10 
            if tambahan_poin > 0:
                profil_siswa.total_poin += tambahan_poin
                profil_siswa.save()
        
        # ... (Logika lencana Anda tetap sama) ...
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
            "hasil_review": hasil_review  # <-- KIRIM DATA REVIEW KE TEMPLATE
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
    
    # --- PERBAIKAN DI SINI ---
    return JsonResponse({"error": "Data tidak ditemukan"}, status=404)
    # --- AKHIR PERBAIKAN ---


def api_rantai_makanan_view(request):
    data_ekosistem = {"nama": "Rawa Gambut", "organisme": [
        {"id": 1, "nama": "Fitoplankton", "tipe": "produsen", "memakan": []},
        {"id": 2, "nama": "Udang Kecil", "tipe": "konsumen_1", "memakan": [1]},
        {"id": 3, "nama": "Ikan Haruan", "tipe": "konsumen_2", "memakan": [2]},
        {"id": 4, "nama": "Bangau", "tipe": "konsumen_3", "memakan": [3]},
    ]}
    return JsonResponse(data_ekosistem)


@login_required
@user_passes_test(is_siswa, login_url="/login/")
def duel_simbiosis_view(request):
    
    try:
        materi_asal = SubTopik.objects.get(judul="1.2: Membedah Interaksi Makhluk Hidup di Rawa")
        materi_asal_pk = materi_asal.pk
    except SubTopik.DoesNotExist:
        materi_asal_pk = None

    sumber_akses = request.GET.get('dari', 'materi')

    # --- UPDATE DATA GAME DENGAN GAMBAR LOKAL PER SOAL ---
    game_data = [
        {
            "level": 1,
            "questions": [
                {
                    "id": 101,
                    "image_url": "/static/images/duel_simbiosis/level1_soal1.jpg", # Bakteri
                    "soal": "Bakteri pengikat nitrogen yang hidup di bintil akar tanaman polong-polongan.",
                    "jawaban_benar": "Mutualisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                },
                {
                    "id": 102,
                    "image_url": "/static/images/duel_simbiosis/level1_soal2.jpg", # Cacing Pita
                    "soal": "Cacing pita yang hidup di dalam usus manusia dan menyerap sari makanan.",
                    "jawaban_benar": "Parasitisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                }
            ]
        },
        {
            "level": 2,
            "questions": [
                {
                    "id": 201,
                    "image_url": "/static/images/duel_simbiosis/level2_soal1.jpg", # Hiu Remora
                    "soal": "Ikan remora yang berenang di dekat ikan hiu untuk mendapatkan sisa makanan.",
                    "jawaban_benar": "Komensalisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                },
                {
                    "id": 202,
                    "image_url": "/static/images/duel_simbiosis/level2_soal2.jpg", # Tali Putri
                    "soal": "Tali putri yang melilit tanaman inang dan mengambil nutrisinya.",
                    "jawaban_benar": "Parasitisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                }
            ]
        },
        {
            "level": 3,
            "questions": [
                {
                    "id": 301,
                    "image_url": "/static/images/duel_simbiosis/level3_soal1.jpg", # Lebah Bunga
                    "soal": "Lebah yang mengambil nektar dari bunga sambil membantu penyerbukan.",
                    "jawaban_benar": "Mutualisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                },
                {
                    "id": 302,
                    "image_url": "/static/images/duel_simbiosis/level3_soal2.jpg", # Anggrek
                    "soal": "Tanaman anggrek yang menempel pada pohon mangga untuk mendapatkan cahaya matahari.",
                    "jawaban_benar": "Komensalisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                }
            ]
        },
        {
            "level": 4,
            "questions": [
                {
                    "id": 401,
                    "image_url": "/static/images/duel_simbiosis/level4_soal1.jpg", # Nyamuk
                    "soal": "Nyamuk yang menggigit kulit manusia untuk menghisap darah.",
                    "jawaban_benar": "Parasitisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                },
                {
                    "id": 402,
                    "image_url": "/static/images/duel_simbiosis/level4_soal2.jpg", # Jalak Kerbau
                    "soal": "Burung jalak yang memakan kutu di punggung kerbau.",
                    "jawaban_benar": "Mutualisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                }
            ]
        },
        {
            "level": 5,
            "questions": [
                {
                    "id": 501,
                    "image_url": "/static/images/duel_simbiosis/level5_soal1.jpg", # Sirih
                    "soal": "Sirih yang merambat pada tumbuhan inangnya untuk mencari cahaya matahari.",
                    "jawaban_benar": "Komensalisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                },
                {
                    "id": 502,
                    "image_url": "/static/images/duel_simbiosis/level5_soal2.jpg", # Kutu Rambut
                    "soal": "Kutu rambut yang hidup di kepala manusia.",
                    "jawaban_benar": "Parasitisme",
                    "pilihan": ["Mutualisme", "Komensalisme", "Parasitisme"]
                }
            ]
        },
    ]
    # --- AKHIR UPDATE ---

    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)

    context = {
        "game_data_json": mark_safe(json.dumps(game_data)),
        "profil_siswa": profil_siswa,
        "materi_asal_pk": materi_asal_pk,
        "sumber_akses": sumber_akses, 
    }
    return render(request, "core/arena_duel_simbiosis.html", context)


@login_required
@require_POST
@user_passes_test(is_siswa, login_url="/login/")
def api_simpan_jawaban_view(request):
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


# Di dalam core/views.py

@login_required
@user_passes_test(is_siswa, login_url="/login/")
def jejak_predator_view(request):
    
    try:
        materi_asal = SubTopik.objects.get(judul="1.2: Membedah Interaksi Makhluk Hidup di Rawa")
        materi_asal_pk = materi_asal.pk
    except SubTopik.DoesNotExist:
        materi_asal_pk = None

    sumber_akses = request.GET.get('dari', 'materi')

    game_data = [
        {
            "level": 1,
            "title": "Misteri di Tepi Sungai",
            "steps": [
                {
                    "text": "Di tepi sungai yang dikelilingi rimbunnya pohon bakau, seekor biawak air sedang mengintai sarang burung bangau untuk memakan telur-telurnya.",
                    "image_url": "/static/images/jejak_predator/level1_step1.jpg", # Gambar 1
                    "question": "Dalam cerita ini, siapakah yang berperan sebagai predator?",
                    "options": ["Burung Bangau", "Biawak Air", "Telur", "Pohon Bakau"],
                    "correct_answer": "Biawak Air"
                },
                {
                    "text": "Sang biawak berhasil mendapatkan telur tersebut. Namun, saat ia lengah, seekor elang rawa yang lebih besar mengincarnya dari atas...",
                    "image_url": "/static/images/jejak_predator/level1_step2.jpg", # Gambar 2
                    "question": None
                },
                {
                    "text": "Dengan cepat, elang rawa itu menukik dan menyambar biawak air tersebut!",
                    "image_url": "/static/images/jejak_predator/level1_step3.jpg", # Gambar 3
                    "question": "Siapa yang menjadi konsumen puncak dalam rantai makanan pendek ini?",
                    "options": ["Burung Bangau", "Biawak Air", "Elang Rawa"],
                    "correct_answer": "Elang Rawa"
                }
            ]
        },
        {
            "level": 2,
            "title": "Penyergapan Ikan Toman",
            "steps": [
                {
                    "text": "Di kedalaman air rawa yang tenang, seekor katak sedang berenang santai di antara akar eceng gondok.",
                    "image_url": "/static/images/jejak_predator/level2_step1.jpg",
                    "question": None
                },
                {
                    "text": "Tiba-tiba, bayangan gelap melesat! Ikan Toman dengan gigi tajamnya menyambar katak tersebut.",
                    "image_url": "/static/images/jejak_predator/level2_step2.jpg",
                    "question": "Hubungan antara Ikan Toman dan Katak disebut...",
                    "options": ["Kompetisi", "Predasi", "Mutualisme", "Parasitisme"],
                    "correct_answer": "Predasi"
                },
                {
                    "text": "Ikan Toman adalah predator ganas. Jika populasi katak habis dimakan, apa yang mungkin terjadi pada populasi Toman?",
                    "image_url": "/static/images/jejak_predator/level2_step3.jpg",
                    "question": "Analisis dampaknya:",
                    "options": ["Populasi Toman akan meningkat pesat", "Populasi Toman akan menurun karena kurang makanan", "Tidak berpengaruh apa-apa"],
                    "correct_answer": "Populasi Toman akan menurun karena kurang makanan"
                }
            ]
        },
        {
            "level": 3,
            "title": "Si Pemburu Malam",
            "steps": [
                {
                    "text": "Malam hari di rawa gambut. Seekor tikus rawa keluar mencari makan. Ia tidak sadar ada sepasang mata mengawasinya.",
                    "image_url": "/static/images/jejak_predator/level3_step1.jpg",
                    "question": None
                },
                {
                    "text": "Seekor Ular Sanca (Python) meluncur tanpa suara dan melilit tikus itu.",
                    "image_url": "/static/images/jejak_predator/level3_step2.jpg",
                    "question": "Dalam skenario ini, Tikus berperan sebagai...",
                    "options": ["Predator", "Mangsa (Prey)", "Produsen", "Pengurai"],
                    "correct_answer": "Mangsa (Prey)"
                },
                 {
                    "text": "Ular tersebut kemudian beristirahat untuk mencerna makanannya.",
                    "image_url": "/static/images/jejak_predator/level3_step3.jpg",
                    "question": "Ular mengendalikan populasi tikus agar tidak meledak. Ini adalah fungsi predator sebagai...",
                    "options": ["Pengganggu ekosistem", "Penyeimbang populasi (Biocontrol)", "Perusak tanaman"],
                    "correct_answer": "Penyeimbang populasi (Biocontrol)"
                }
            ]
        }
    ]

    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)

    context = {
        "game_data_json": mark_safe(json.dumps(game_data)),
        "profil_siswa": profil_siswa,
        "materi_asal_pk": materi_asal_pk,
        "sumber_akses": sumber_akses,
    }
    return render(request, "core/arena_jejak_predator.html", context)


@login_required
@user_passes_test(is_siswa, login_url="/login/")
def progres_view(request):
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

# Di dalam core/views.py
# ... (pastikan json, mark_safe, ProfilSiswa, SubTopik sudah diimpor di atas) ...

@login_required
@user_passes_test(is_siswa, login_url="/login/")
def klasifikasi_view(request):
    
    # 1. Dapatkan ID materi 1.1
    try:
        materi_asal = SubTopik.objects.get(judul="1.1: Mengenal Penghuni Lahan Basah")
        materi_asal_pk = materi_asal.pk
    except SubTopik.DoesNotExist:
        materi_asal_pk = None

    # 2. Data Game 5 Level (DENGAN GAMBAR LOKAL)
    game_data = [
        {
            "level": 1,
            "image_url": "/static/images/klasifikasi_komponen/level1.jpg", # Pastikan file ini ada
            "items": [
                {"nama": "Ikan Papuyu", "tipe": "biotik"},
                {"nama": "Tanaman Purun", "tipe": "biotik"},
                {"nama": "Bekantan", "tipe": "biotik"},
                {"nama": "Tanah Rawa", "tipe": "abiotik"},
                {"nama": "Cahaya Matahari", "tipe": "abiotik"},
                {"nama": "Air Gambut", "tipe": "abiotik"},
            ]
        },
        {
            "level": 2,
            "image_url": "/static/images/klasifikasi_komponen/level2.jpg",
            "items": [
                {"nama": "Ikan Haruan", "tipe": "biotik"},
                {"nama": "Suhu Udara", "tipe": "abiotik"},
                {"nama": "Siput Air", "tipe": "biotik"},
                {"nama": "Kelembapan", "tipe": "abiotik"},
                {"nama": "Bakteri", "tipe": "biotik"},
            ]
        },
        {
            "level": 3,
            "image_url": "/static/images/klasifikasi_komponen/level3.jpg",
            "items": [
                {"nama": "Burung Bangau", "tipe": "biotik"},
                {"nama": "Fitoplankton", "tipe": "biotik"},
                {"nama": "Batu", "tipe": "abiotik"},
                {"nama": "Jamur", "tipe": "biotik"},
                {"nama": "Oksigen (O2)", "tipe": "abiotik"},
            ]
        },
        {
            "level": 4,
            "image_url": "/static/images/klasifikasi_komponen/level4.jpg",
            "items": [
                {"nama": "Pohon Galam", "tipe": "biotik"},
                {"nama": "Serangga Air", "tipe": "biotik"},
                {"nama": "Angin", "tipe": "abiotik"},
                {"nama": "Ikan Sepat", "tipe": "biotik"},
                {"nama": "Nutrien (Hara)", "tipe": "abiotik"},
            ]
        },
        {
            "level": 5,
            "image_url": "/static/images/klasifikasi_komponen/level5.jpg",
            "items": [
                {"nama": "Biawak Air", "tipe": "biotik"},
                {"nama": "pH Tanah", "tipe": "abiotik"},
                {"nama": "Pohon Rumbia", "tipe": "biotik"},
                {"nama": "Elang Rawa", "tipe": "biotik"},
                {"nama": "Mineral", "tipe": "abiotik"},
            ]
        },
    ]

    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)

    context = {
        "game_data_json": mark_safe(json.dumps(game_data)),
        "profil_siswa": profil_siswa,
        "materi_asal_pk": materi_asal_pk,
    }
    return render(request, "core/arena_klasifikasi.html", context)

@login_required
@user_passes_test(is_siswa, login_url="/login/") # Pastikan hanya siswa yang bisa lihat
def leaderboard_view(request):
    
    # 1. Ambil semua profil siswa, urutkan dari poin tertinggi
    semua_profil_siswa = ProfilSiswa.objects.filter(user__role="Siswa").order_by('-total_poin')

    # 2. Ubah queryset menjadi list agar kita bisa cari ranking
    daftar_peringkat = list(semua_profil_siswa)

    # 3. Cari tahu peringkat siswa yang sedang login
    peringkat_saat_ini = 0
    profil_saat_ini = request.user.profilsiswa # Asumsi relasi 'profilsiswa'
    
    for i, profil in enumerate(daftar_peringkat):
        if profil.user == request.user:
            peringkat_saat_ini = i + 1 # i+1 karena list index dimulai dari 0
            break

    context = {
        'daftar_peringkat': daftar_peringkat, # Daftar lengkap untuk di-loop
        'peringkat_saat_ini': peringkat_saat_ini, # Angka (misal: 5)
        'profil_saat_ini': profil_saat_ini, # Objek profil (untuk poin)
    }
    return render(request, "core/leaderboard.html", context)

@login_required
@user_passes_test(is_siswa, login_url="/login/")
def ujian_akhir_view(request):
    
    # --- Cek Prasyarat ---
    total_materi = SubTopik.objects.count()
    materi_selesai = UserMateriProgress.objects.filter(user=request.user).count()
    
    if materi_selesai < total_materi:
        messages.error(request, "Anda harus menyelesaikan SEMUA materi ekspedisi sebelum bisa mengambil Ujian Akhir.")
        return redirect('dashboard')
    
    # Ambil (misal) 20 soal acak dari SEMUA kuis
    JUMLAH_SOAL = 20 
    
    if request.method == "POST":
        # --- LOGIKA PENILAIAN (POST) ---
        
        # Ambil ID pertanyaan dari form yang dikirim
        pertanyaan_ids = [key.split('_')[1] for key in request.POST if key.startswith('pertanyaan_')]
        semua_pertanyaan = Pertanyaan.objects.filter(id__in=pertanyaan_ids).prefetch_related('pilihan')
        
        total_pertanyaan = semua_pertanyaan.count()
        jawaban_benar = 0
        hasil_review = []

        for pertanyaan in semua_pertanyaan:
            jawaban_pengguna_id = request.POST.get(f"pertanyaan_{pertanyaan.id}")
            is_correct_answer = False
            pilihan_pengguna = None
            pilihan_benar = None

            try:
                pilihan_benar = pertanyaan.pilihan.get(is_benar=True)
            except PilihanJawaban.DoesNotExist:
                continue 

            if jawaban_pengguna_id:
                try:
                    pilihan_pengguna = PilihanJawaban.objects.get(id=jawaban_pengguna_id)
                    if pilihan_pengguna == pilihan_benar:
                        jawaban_benar += 1
                        is_correct_answer = True
                except PilihanJawaban.DoesNotExist:
                    pass 

            # Simpan ke log
            QuizAttemptLog.objects.create(
                user=request.user, question=pertanyaan, is_correct=is_correct_answer
            )
            
            hasil_review.append({
                'pertanyaan': pertanyaan,
                'pilihan_pengguna': pilihan_pengguna,
                'pilihan_benar': pilihan_benar,
                'is_correct': is_correct_answer
            })

        skor_saat_ini = (jawaban_benar / total_pertanyaan) * 100 if total_pertanyaan > 0 else 0
        
        # Beri Poin Bonus & Lencana Juara
        profil_siswa = request.user.profilsiswa
        lencana_baru_didapat = []
        if skor_saat_ini >= 75: # Batas lulus 75
            profil_siswa.total_poin += 100 # Bonus 100 poin karena lulus
            profil_siswa.save()
            
            try:
                # (Pastikan Anda telah membuat lencana ini di admin)
                lencana_juara = Lencana.objects.get(nama="Juara EkoSphere")
                if lencana_juara not in profil_siswa.lencana.all():
                    profil_siswa.lencana.add(lencana_juara)
                    lencana_baru_didapat.append(lencana_juara)
            except Lencana.DoesNotExist:
                print("LOG: Lencana 'Juara EkoSphere' tidak ditemukan di database.")
        
        # Render halaman hasil kuis yang sudah ada
        context = {
            "skor": skor_saat_ini,
            "kuis": {"judul": "Ujian Akhir EkoSphere"}, # Buat objek kuis tiruan
            "lencana_baru": lencana_baru_didapat,
            "hasil_review": hasil_review,
        }
        return render(request, "core/kuis_hasil.html", context)

    else:
        # --- LOGIKA TAMPILKAN SOAL (GET) ---
        daftar_soal = Pertanyaan.objects.prefetch_related('pilihan').order_by('?')[:JUMLAH_SOAL]
        
        context = {
            'kuis': {'judul': 'Ujian Akhir EkoSphere'},
            'daftar_soal': daftar_soal
        }
        return render(request, "core/ujian_akhir.html", context)
    
@login_required
@require_POST
@user_passes_test(is_siswa, login_url="/login/")
def api_simpan_poin_view(request):
    data = json.loads(request.body)
    poin_didapat = data.get("poin_didapat", 0)

    if poin_didapat > 0:
        try:
            profil_siswa = request.user.profilsiswa
            profil_siswa.total_poin += poin_didapat
            profil_siswa.save()
            return JsonResponse(
                {"status": "sukses", "total_poin_baru": profil_siswa.total_poin}
            )
        except ProfilSiswa.DoesNotExist:
            return JsonResponse(
                {"status": "gagal", "error": "Profil siswa tidak ditemukan"}, status=404
            )
    return JsonResponse(
        {"status": "gagal", "error": "Tidak ada poin untuk ditambahkan"}, status=400
    )

# Di dalam core/views.py

@login_required
@user_passes_test(is_siswa, login_url="/login/")
def energy_flow_view(request):
    
    # Cari PK materi 1.3 untuk tombol "Kembali"
    try:
        materi_asal = SubTopik.objects.get(judul="1.3: Membangun Jaring-jaring Makanan Lahan Basah")
        materi_asal_pk = materi_asal.pk
    except SubTopik.DoesNotExist:
        materi_asal_pk = None

    # Data untuk 5 Level Rantai Makanan
    game_data = [
        {
            "level": 1,
            "title": "Rantai Rawa Sederhana",
            # GANTI DENGAN GAMBAR LOKAL
            "image_url": "/static/images/energy_flow/level1.jpg", 
            "organisms": [
                {"id": 1, "nama": "Fitoplankton", "tipe": "produsen", "memakan": []},
                {"id": 2, "nama": "Udang Kecil", "tipe": "konsumen_1", "memakan": [1]},
                {"id": 3, "nama": "Ikan Haruan", "tipe": "konsumen_2", "memakan": [2]}
            ]
        },
        {
            "level": 2,
            "title": "Jalur Burung",
            # GANTI DENGAN GAMBAR LOKAL
            "image_url": "/static/images/energy_flow/level2.jpg", 
            "organisms": [
                {"id": 1, "nama": "Tanaman Purun", "tipe": "produsen", "memakan": []},
                {"id": 2, "nama": "Siput Air", "tipe": "konsumen_1", "memakan": [1]},
                {"id": 3, "nama": "Ikan Papuyu", "tipe": "konsumen_2", "memakan": [2]},
                {"id": 4, "nama": "Burung Bangau", "tipe": "konsumen_3", "memakan": [3]}
            ]
        },
        {
            "level": 3,
            "title": "Puncak Rantai Makanan",
            # GANTI DENGAN GAMBAR LOKAL
            "image_url": "/static/images/energy_flow/level3.jpg",
            "organisms": [
                {"id": 1, "nama": "Rumput Rawa", "tipe": "produsen", "memakan": []},
                {"id": 2, "nama": "Belalang", "tipe": "konsumen_1", "memakan": [1]},
                {"id": 3, "nama": "Katak", "tipe": "konsumen_2", "memakan": [2]},
                {"id": 4, "nama": "Biawak Air", "tipe": "konsumen_3", "memakan": [3]}
            ]
        },
        {
            "level": 4,
            "title": "Jejak Mamalia",
            # GANTI DENGAN GAMBAR LOKAL
            "image_url": "/static/images/energy_flow/level4.jpg",
            "organisms": [
                {"id": 1, "nama": "Pohon Rumbia", "tipe": "produsen", "memakan": []},
                {"id": 2, "nama": "Bekantan", "tipe": "konsumen_1", "memakan": [1]},
                {"id": 3, "nama": "Manusia", "tipe": "konsumen_2", "memakan": [2]}
            ]
        },
        {
            "level": 5,
            "title": "Penguasa Udara",
            # GANTI DENGAN GAMBAR LOKAL
            "image_url": "/static/images/energy_flow/level5.jpg",
            "organisms": [
                {"id": 1, "nama": "Padi Rawa", "tipe": "produsen", "memakan": []},
                {"id": 2, "nama": "Tikus", "tipe": "konsumen_1", "memakan": [1]},
                {"id": 3, "nama": "Ular Sawah", "tipe": "konsumen_2", "memakan": [2]},
                {"id": 4, "nama": "Elang Rawa", "tipe": "konsumen_3", "memakan": [3]}
            ]
        }
    ]

    profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)

    context = {
        "game_data_json": mark_safe(json.dumps(game_data)),
        "profil_siswa": profil_siswa,
        "materi_asal_pk": materi_asal_pk,
    }
    return render(request, "core/arena_energy_flow.html", context)

@login_required
@require_POST
def api_update_waktu_view(request):
    """API untuk menerima heartbeat dan update waktu akses siswa"""
    if request.user.role == "Siswa":
        try:
            profil = request.user.profilsiswa
            # Tambahkan 60 detik (1 menit) setiap kali dipanggil
            profil.total_waktu_akses += 60 
            profil.save()
            return JsonResponse({"status": "sukses"})
        except ProfilSiswa.DoesNotExist:
            return JsonResponse({"status": "gagal"}, status=404)
    return JsonResponse({"status": "diabaikan"})

def referensi_view(request):
    semua_buku = [
        {
            "judul": "Ilmu Pengetahuan Alam untuk SMA/MA Kelas X",
            "kategori": "Buku Paket IPA",
            "penulis": "Ayuk Ratna Puspaningsih, Elizabeth Tjahjadarmawan, Niken Resminingpuri Krisdianti",
            "tahun": "2021",
            "penerbit": "Pusat Kurikulum dan Perbukuan - Badan Penelitian dan Pengembangan dan Perbukuan",
            "deskripsi": "Buku teks utama yang membahas dasar-dasar ekosistem, komponen biotik, dan abiotik secara umum.",
            "image_filename": "cover_ipa.png", 
            "pdf_filename": "buku_ipa.pdf" 
        },
        {
            "judul": "Buku Ajar Pengantar Lahan Basah",
            "kategori": "Referensi Lahan Basah",
            "penulis": "Kissinger, Gusti Muhammad Hatta, Moch.Arief Soendjoto, Zainal Abidin",
            "tahun": "2023",
            "penerbit": "CV Banyubening Cipta Sejahtera",
            "deskripsi": "Panduan lengkap mengenai flora dan fauna endemik di rawa gambut Kalimantan Selatan.",
            "image_filename": "cover_lahan_basah.png",
            "pdf_filename": "buku_lahan_basah.pdf"
        },
        {
            "judul": "Modul Ajar EkoSphere",
            "kategori": "Modul Pembelajaran",
            "penulis": "Muhammad Dimas Aditya, Muhammad Farros Shofiy",
            "tahun": "2025",
            "penerbit": "PILKOM 2023 FKIP ULM",
            "deskripsi": "Modul interaktif khusus yang dirancang untuk menemani pembelajaran di website EkoSphere.",
            "image_filename": "cover_modul.png",
            "pdf_filename": "modul_ekosphere.pdf"
        }
    ]

    context = {
        "semua_buku": semua_buku,
    }
    return render(request, 'core/referensi.html', context)