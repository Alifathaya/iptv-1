# Jelasin — Native Android AI Photo Enhancer

Kotlin + Jetpack Compose app untuk memperjelas foto buram, pecah, dan noisy.

## Fitur

- **AI Presets:** Natural, Perbaiki Wajah, Upscale 2x, Upscale 4x (Cloud), Kurangi Noise
- **Konvolusi ketajaman 3×3** di `Dispatchers.Default` (coroutine background)
- **TensorFlow Lite** on-device (opsional model `assets/enhance_sr.tflite`) + fallback neural upscale
- **Cloud GPU** Real-ESRGAN via FastAPI (`/v1/enhance`)
- **CameraX** dengan blur detection (peringatan goyang)
- **Before/After slider** interaktif
- **Room** history di home screen
- **MediaStore** simpan ke `Pictures/Jelasin`
- **Material 3** dark theme, animasi scanning line saat proses

## Arsitektur MVVM

```
ui/          → Compose screens + ViewModels
ml/          → ConvolutionSharpen, LocalEnhanceEngine, CloudEnhanceClient, TfliteEnhancer
data/        → Room database + HistoryRepository
util/        → ImageDecoder loader, MediaStore saver, BlurDetector
```

## Build

```bash
cd jelasin-android
./gradlew assembleDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`

## Cloud API

Atur URL server GPU di layar enhance (sama dengan backend `backend/` di repo ini).

Contoh: `https://your-gpu-server:8080`

## TFLite model (opsional)

Letakkan file model super-resolution di:
`app/src/main/assets/enhance_sr.tflite`

Tanpa model, upscale 2x memakai fallback edge-aware reconstruction.
