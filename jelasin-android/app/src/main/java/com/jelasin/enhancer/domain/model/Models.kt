package com.jelasin.enhancer.domain.model

enum class EnhancePreset(
    val label: String,
    val description: String,
) {
    NATURAL("Natural", "Ketajaman halus & warna asli"),
    FACE("Perbaiki Wajah", "Fokus detail wajah & noise ringan"),
    UPSCALE_2X("Upscale 2x", "Tingkatkan resolusi 2× dengan AI lokal"),
    UPSCALE_4X("Upscale 4x", "Super resolution 4× (cloud AI)"),
    DENOISE("Kurangi Noise", "Hilangkan grain & noise"),
}

enum class EnhanceEngine {
    LOCAL,
    TFLITE,
    CLOUD,
}

data class EnhanceRequest(
    val preset: EnhancePreset,
    val sharpness: Float = 0.45f,
    val cloudApiUrl: String = "",
    val cloudApiKey: String = "",
)

data class EnhanceResult(
    val bitmap: android.graphics.Bitmap,
    val engineUsed: EnhanceEngine,
    val outputWidth: Int,
    val outputHeight: Int,
)

data class HistoryItem(
    val id: Long = 0,
    val originalPath: String,
    val enhancedPath: String,
    val preset: String,
    val createdAt: Long,
    val width: Int,
    val height: Int,
)
