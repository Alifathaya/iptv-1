# Foto Jelas Pro v2 — web preview

Design baru: Perjelas / Warnai B&W / Full Restore via Replicate API.
File statis, tanpa build. Token Replicate hanya di browser (localStorage), khusus testing.

## Cara periksa (pilih satu)

Opsi A — di VPS ini:
```
cd /tmp/fotojelas-v2/docs/fotojelas-v2 && python3 -m http.server 8099
# buka http://173.249.25.166:8099/  (atau via ssh tunnel)
```

Opsi B — di komputer lokal:
```
git clone https://github.com/Alifathaya/iptv-1.git
git checkout web/fotojelas-v2-restore
cd iptv-1/docs/fotojelas-v2 && python3 -m http.server 8099
# buka http://localhost:8099/
```

## Isi token gratis
1. Daftar replicate.com → replicate.com/account/api-tokens
2. Tempel token di panel Pengaturan API → Simpan
3. Upload foto → pilih mode → tekan tombol
4. Tanpa token: pakai tombol "Coba tanpa token" (demo lokal, bukan AI)

## Estimasi biaya
DDColor ~0.001 USD, CodeFormer ~0.003 USD, ESRGAN 0.005-0.03 USD per foto.

## Naik APK
Kalau design oke: `capacitor.config` webDir diarahkan ke folder ini,
lalu ikut BUILD-APK.md yang lama. Token wajib pindah ke backend proxy.
