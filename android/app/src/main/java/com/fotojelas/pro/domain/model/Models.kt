package com.fotojelas.pro.domain.model

enum class EnhancePreset(
    val label: String,
    val description: String,
) {
    NATURAL("Natural", "Ketajaman halus & warna asli"),
    JELAS("Jelas", "Lebih tajam & kontras"),
    PORTRAIT("Portrait", "Optimal untuk wajah"),
    PRO_BLUR("Foto Buram", "Deblur Pro + ketajaman"),
    DOCUMENT("Dokumen", "Teks & dokumen tajam"),
    DENOISE("Kurangi Noise", "Hilangkan grain & noise"),
    UPSCALE_2X("Upscale 2x", "AI lokal tingkatkan resolusi 2×"),
    AI_4X("AI 4x", "ESRGAN super resolution 4×"),
    ULTRA_8X("Ultra 8x", "ESRGAN super resolution 8×"),
    CLOUD_4X("GPU 4x", "Cloud Real-ESRGAN 4×"),
    CLOUD_8X("GPU 8x MAX", "Cloud Real-ESRGAN 8×"),
}

enum class EnhanceEngine {
    LOCAL,
    TFLITE,
    CLOUD,
}

data class EnhanceRequest(
    val preset: EnhancePreset,
    val sharpness: Float = 0.45f,
    val clarity: Float = 0.22f,
    val contrast: Float = 0.18f,
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
