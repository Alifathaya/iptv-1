# Cara Build APK — Foto Jelas Pro

Aplikasi Android menggunakan **Capacitor** — web app yang dibungkus jadi APK native.

## Yang Anda dapat

- APK installable di Android (tanpa Play Store)
- Simpan foto ke Documents
- Bagikan langsung ke WhatsApp / Telegram
- Mode **ULTRA 8x** AI default di app native
- Semua fitur web + akses galeri

---

## Persiapan (sekali saja)

### 1. Install software

| Software | Download |
|----------|----------|
| **Node.js** 18+ | https://nodejs.org |
| **Android Studio** | https://developer.android.com/studio |

Di Android Studio, buka **SDK Manager** dan install:
- Android SDK Platform 34
- Android SDK Build-Tools

### 2. Clone & install

```bash
git clone https://github.com/Alifathaya/iptv-1.git
cd iptv-1
npm install
```

---

## Build APK (debug — untuk testing)

```bash
npm run build:android
```

Buka Android Studio:

```bash
npx cap open android
```

Di Android Studio:
1. Tunggu Gradle sync selesai
2. **Build → Build Bundle(s) / APK(s) → Build APK(s)**
3. APK ada di: `android/app/build/outputs/apk/debug/app-debug.apk`

Copy APK ke HP → install (izinkan "Install from unknown sources").

---

## Build APK release (untuk distribusi)

1. Di Android Studio: **Build → Generate Signed Bundle / APK**
2. Pilih **APK**
3. Buat keystore baru (simpan password dengan aman!)
4. Pilih **release** build variant
5. APK release: `android/app/build/outputs/apk/release/app-release.apk`

---

## Setelah mengubah kode web

Setiap kali edit file di `docs/photo-enhancer/`:

```bash
npm run cap:sync
```

Lalu build ulang di Android Studio.

---

## Perintah npm

| Perintah | Fungsi |
|----------|--------|
| `npm run build:photo` | Bundle JS + Capacitor |
| `npm run cap:sync` | Sync web ke Android |
| `npm run build:android` | Build photo + sync |
| `npx cap open android` | Buka di Android Studio |

---

## Alternatif tanpa Android Studio

### PWA (lebih mudah)

1. Buka di Chrome Android: `https://alifathaya.github.io/iptv-1/photo-enhancer/`
2. Menu → **Tambahkan ke Layar Utama**
3. Berfungsi seperti app (tanpa APK)

### Online build (CI)

Bisa setup GitHub Actions untuk build APK otomatis — butuh signing key.

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| AI tidak load | Pastikan internet aktif (model diunduh pertama kali) |
| Proses lambat | Gunakan mode Pro/Cepat, atau foto lebih kecil |
| Gradle error | Update Android Studio + SDK 34 |
| Install gagal | Aktifkan "Install unknown apps" untuk file manager |

---

## Catatan teknis

- **Package:** `com.fotojelas.pro`
- **Min SDK:** Android 6+ (API 22)
- **Target SDK:** 34
- AI model diunduh dari CDN saat pertama dipakai (~5–15MB)
