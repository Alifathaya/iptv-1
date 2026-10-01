# Foto Jelas Pro v2 — web preview

Design baru: Perjelas / Warnai B&W / Full Restore via fal.ai API.
File statis + proxy VPS, tanpa build. Key fal.ai hanya di browser (localStorage), khusus testing.

## Cara periksa (pilih satu)

Opsi A — di VPS ini (proxy + web jalan di port 8099):
```
# buka http://173.249.25.166:8099/
```

Opsi B — di komputer lokal:
```
git clone https://github.com/Alifathaya/iptv-1.git
git checkout web/fotojelas-v2-restore
cd iptv-1/docs/fotojelas-v2 && python3 -m http.server 8099
# buka http://localhost:8099/
```

## Isi key gratis ($10)
1. Daftar fal.ai → fal.ai/dashboard/keys → buat key baru
2. Tempel key di panel Pengaturan API → Simpan
3. Upload foto → pilih mode → tekan tombol
4. Tanpa key: pakai tombol "Coba tanpa token" (demo lokal, bukan AI)

## Estimasi biaya fal.ai
CodeFormer ~0.0021 USD/megapixel, DDColor murah per gambar.

## Naik APK
Kalau design oke: `capacitor.config` webDir diarahkan ke folder ini,
lalu ikut BUILD-APK.md yang lama. Token wajib pindah ke backend proxy.
