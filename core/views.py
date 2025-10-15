# core/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .forms import CustomUserCreationForm

# TAMBAHKAN 'PertanyaanArena' DI BARIS INI
from .models import (
    User,
    Topik,
    SubTopik,
    Kuis,
    HasilKuis,
    ProfilSiswa,
    Lencana,
    PertanyaanArena,
)

# ... (sisa kode view Anda tidak perlu diubah) ...


# Hapus 'Materi', tambahkan 'Topik' dan 'SubTopik'
from .models import (
    Topik,
    SubTopik,
    Kuis,
    HasilKuis,
    ProfilSiswa,
    Lencana,
)  # Tambahkan HasilKuis & ProfilSiswa
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.utils.safestring import mark_safe


@login_required
def dashboard_view(request):
    if request.user.role == "Guru":
        materi_guru = SubTopik.objects.filter(pembuat=request.user)

        # --- LOGIKA BARU UNTUK ANALISIS GURU ---

        # 1. Analisis Peta Kesulitan Konsep (sudah ada)
        pertanyaan_sulit = (
            PertanyaanArena.objects.annotate(
                jumlah_salah=Count(
                    "jawaban_siswa", filter=Q(jawaban_siswa__jawaban_benar=False)
                )
            )
            .filter(jumlah_salah__gt=0)
            .order_by("-jumlah_salah")[:5]
        )

        # 2. Analisis Tingkat Penyelesaian Misi
        total_siswa = User.objects.filter(role="Siswa").count()
        # Hitung siswa unik yang pernah mengerjakan kuis ATAU arena
        siswa_yang_mengerjakan = (
            User.objects.filter(
                Q(hasilkuis__isnull=False) | Q(jawabansiswa__isnull=False)
            )
            .distinct()
            .count()
        )
        persentase_penyelesaian = (
            (siswa_yang_mengerjakan / total_siswa) * 100 if total_siswa > 0 else 0
        )

        # 3. Analisis Identifikasi Siswa
        siswa_berprestasi = ProfilSiswa.objects.order_by("-total_poin")[
            :3
        ]  # 3 siswa teratas
        siswa_perlu_perhatian = ProfilSiswa.objects.order_by("total_poin")[
            :3
        ]  # 3 siswa terbawah

        context = {
            "daftar_materi": materi_guru,
            "pertanyaan_sulit": pertanyaan_sulit,
            "persentase_penyelesaian": persentase_penyelesaian,
            "total_siswa": total_siswa,
            "siswa_berprestasi": siswa_berprestasi,
            "siswa_perlu_perhatian": siswa_perlu_perhatian,
        }
        return render(request, "core/teacher_dashboard.html", context)
    else:
        # --- LOGIKA BARU UNTUK PROGRES LENCANA ---
        profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
        hasil_kuis_siswa = HasilKuis.objects.filter(siswa=request.user)
        semua_subtopik = SubTopik.objects.all()
        completed_quiz_ids = set(hasil_kuis_siswa.values_list("kuis_id", flat=True))

        # Cari lencana berikutnya yang bisa diraih
        lencana_selanjutnya = (
            Lencana.objects.exclude(id__in=profil_siswa.lencana.all())
            .order_by("syarat_poin")
            .first()
        )

        progres_persen = 0
        if lencana_selanjutnya:
            progres_persen = (
                profil_siswa.total_poin / lencana_selanjutnya.syarat_poin
            ) * 100
            if progres_persen > 100:
                progres_persen = 100

        context = {
            "daftar_materi": semua_subtopik,
            "profil_siswa": profil_siswa,
            "hasil_kuis_list": hasil_kuis_siswa,
            "completed_quiz_ids": completed_quiz_ids,
            "lencana_selanjutnya": lencana_selanjutnya,  # Data baru
            "progres_persen": progres_persen,  # Data baru
        }
        return render(request, "core/dashboard.html", context)


@login_required
def subtopik_detail_view(request, pk):
    semua_topik = Topik.objects.all()
    subtopik_aktif = get_object_or_404(SubTopik, pk=pk)

    # --- LOGIKA BARU UNTUK NAVIGASI ---
    # Ambil semua subtopik dalam urutan yang benar
    semua_subtopik_terurut = list(SubTopik.objects.all())

    try:
        # Cari index dari subtopik yang sedang aktif
        current_index = semua_subtopik_terurut.index(subtopik_aktif)

        # Tentukan subtopik sebelumnya (jika ada)
        subtopik_sebelumnya = (
            semua_subtopik_terurut[current_index - 1] if current_index > 0 else None
        )

        # Tentukan subtopik selanjutnya (jika ada)
        subtopik_selanjutnya = (
            semua_subtopik_terurut[current_index + 1]
            if current_index < len(semua_subtopik_terurut) - 1
            else None
        )

    except ValueError:
        # Jika terjadi error (seharusnya tidak), set ke None
        subtopik_sebelumnya = None
        subtopik_selanjutnya = None
    # --- AKHIR LOGIKA BARU ---

    context = {
        "semua_topik": semua_topik,
        "subtopik_aktif": subtopik_aktif,
        "subtopik_sebelumnya": subtopik_sebelumnya,  # Kirim data ke template
        "subtopik_selanjutnya": subtopik_selanjutnya,  # Kirim data ke template
    }
    return render(request, "core/materi_detail.html", context)


@login_required
def kuis_view(request, pk):
    subtopik = get_object_or_404(SubTopik, pk=pk)
    kuis = subtopik.kuis

    if request.method == "POST":
        total_pertanyaan = kuis.pertanyaan.count()
        jawaban_benar = 0

        for pertanyaan in kuis.pertanyaan.all():
            jawaban_pengguna_id = request.POST.get(f"pertanyaan_{pertanyaan.id}")
            if jawaban_pengguna_id:
                pilihan_benar_id = pertanyaan.pilihan.get(is_benar=True).id
                if int(jawaban_pengguna_id) == pilihan_benar_id:
                    jawaban_benar += 1

        skor = (jawaban_benar / total_pertanyaan) * 100 if total_pertanyaan > 0 else 0

        # --- LOGIKA BARU: SIMPAN HASIL DAN POIN ---

        # 1. Simpan atau perbarui skor siswa untuk kuis ini
        HasilKuis.objects.update_or_create(
            siswa=request.user, kuis=kuis, defaults={"skor": skor}
        )

        # 2. Tambah poin ke profil siswa (misal: 10 poin per jawaban benar)
        profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)
        profil_siswa.total_poin += jawaban_benar * 10
        profil_siswa.save()

        # --- LOGIKA BARU: PEMBERIAN LENCANA ---
        lencana_baru_didapat = []
        # Ambil semua lencana yang belum dimiliki siswa
        lencana_yang_belum_dimiliki = Lencana.objects.exclude(profilsiswa=profil_siswa)

        for lencana in lencana_yang_belum_dimiliki:
            # Cek apakah total poin siswa sudah memenuhi syarat
            if profil_siswa.total_poin >= lencana.syarat_poin:
                # Berikan lencana kepada siswa
                profil_siswa.lencana.add(lencana)
                lencana_baru_didapat.append(lencana)
        # --- AKHIR LOGIKA BARU ---

        context = {
            "skor": skor,
            "kuis": kuis,
            "lencana_baru": lencana_baru_didapat,  # Kirim data lencana baru ke template
        }
        return render(request, "core/kuis_hasil.html", context)

    context = {"kuis": kuis}
    return render(request, "core/kuis.html", context)


# View untuk registrasi tidak perlu diubah, tapi pastikan form-nya benar
def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = CustomUserCreationForm()

    context = {"form": form}
    return render(request, "core/register.html", context)


def api_klasifikasi_view(request):
    # Ambil pertanyaan pertama yang bertipe 'klasifikasi'
    pertanyaan = PertanyaanArena.objects.filter(tipe="klasifikasi").first()
    if pertanyaan:
        # Kirim konten JSON-nya sebagai respons
        return JsonResponse(pertanyaan.konten_json)
    return JsonResponse({"error": "Data tidak ditemukan"}, status=404)


def api_rantai_makanan_view(request):
    data_ekosistem = {
        "nama": "Sawah",
        "organisme": [
            {"id": 1, "nama": "Padi", "tipe": "produsen", "memakan": []},
            {"id": 2, "nama": "Tikus", "tipe": "konsumen_1", "memakan": [1]},
            {"id": 3, "nama": "Ular", "tipe": "konsumen_2", "memakan": [2]},
            {"id": 4, "nama": "Elang", "tipe": "konsumen_3", "memakan": [3]},
        ],
    }
    return JsonResponse(data_ekosistem)


@login_required
def duel_simbiosis_view(request):
    pertanyaan_list = PertanyaanArena.objects.filter(tipe="kartu_simbiosis")

    # Buat daftar dari konten JSON dan tambahkan ID
    data_untuk_js = []
    for p in pertanyaan_list:
        konten = p.konten_json
        konten["id"] = p.id  # <-- TAMBAHKAN ID DI SINI
        data_untuk_js.append(konten)

    pertanyaan_json = mark_safe(json.dumps(data_untuk_js))

    context = {"pertanyaan_json": pertanyaan_json}
    return render(request, "core/arena_duel_simbiosis.html", context)


@login_required
@require_POST  # Hanya mengizinkan metode POST
def api_simpan_jawaban_view(request):
    data = json.loads(request.body)
    pertanyaan_id = data.get("pertanyaan_id")
    jawaban_benar = data.get("jawaban_benar")

    try:
        pertanyaan = PertanyaanArena.objects.get(id=pertanyaan_id)

        # Simpan log jawaban siswa
        JawabanSiswa.objects.create(
            siswa=request.user, pertanyaan=pertanyaan, jawaban_benar=jawaban_benar
        )

        # Dapatkan profil siswa
        profil_siswa, created = ProfilSiswa.objects.get_or_create(user=request.user)

        # Jika jawaban benar, tambahkan poin dan cek lencana
        if jawaban_benar:
            profil_siswa.total_poin += 10  # Poin per jawaban benar di arena
            profil_siswa.save()

            # Cek lencana baru
            lencana_yang_belum_dimiliki = Lencana.objects.exclude(
                profilsiswa=profil_siswa
            )
            for lencana in lencana_yang_belum_dimiliki:
                if profil_siswa.total_poin >= lencana.syarat_poin:
                    profil_siswa.lencana.add(lencana)

        return JsonResponse(
            {"status": "sukses", "total_poin_baru": profil_siswa.total_poin}
        )

    except PertanyaanArena.DoesNotExist:
        return JsonResponse(
            {"status": "gagal", "error": "Pertanyaan tidak ditemukan"}, status=404
        )


@login_required
def jejak_predator_view(request):
    # Ambil cerita pertama yang bertipe 'cerita_predator'
    cerita = PertanyaanArena.objects.filter(tipe="cerita_predator").first()

    # Kirim data cerita sebagai JSON yang aman
    cerita_json = mark_safe(json.dumps(cerita.konten_json)) if cerita else None

    context = {
        "cerita_json": cerita_json,
        "pertanyaan_id": cerita.id if cerita else None,
    }
    return render(request, "core/arena_jejak_predator.html", context)


# core/views.py


@login_required
def progres_view(request):
    # Pastikan hanya siswa yang bisa mengakses
    if request.user.role != "Siswa":
        return redirect("dashboard")

    # Ambil semua data progres yang relevan
    profil_siswa = ProfilSiswa.objects.get(user=request.user)
    hasil_kuis = HasilKuis.objects.filter(siswa=request.user).order_by("-waktu_selesai")

    context = {
        "profil_siswa": profil_siswa,
        "hasil_kuis_list": hasil_kuis,
    }
    # Pastikan view ini merender template progres.html
    return render(request, "core/progres.html", context)
