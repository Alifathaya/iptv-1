# Foto Jelas Pro — Android (Native)

Satu aplikasi Android native (Kotlin + Jetpack Compose) — gabungan fitur web + Jelasin.

## Fitur

- **AI Presets:** Natural, Jelas, Portrait, Foto Buram, Dokumen, AI 4x/8x, GPU Cloud 4x/8x
- **CameraX** + deteksi blur (peringatan goyang)
- **Konvolusi 3×3** di coroutine background
- **TensorFlow Lite** on-device + **Cloud Real-ESRGAN**
- **Room** history + **before/after slider**
- **MediaStore** → `Pictures/FotoJelasPro`

## Build

```bash
cd android
./gradlew assembleDebug
```

Atau dari root: `npm run build:android`

APK: `app/build/outputs/apk/debug/app-debug.apk`

Package: `com.fotojelas.pro`

## Web vs Android

- **APK** = app native penuh (rekomendasikan untuk HP)
- **docs/photo-enhancer/** = versi browser (GitHub Pages / preview)
