package com.fotojelas.pro.ml

import android.content.Context
import com.fotojelas.pro.domain.model.EnhanceEngine
import com.fotojelas.pro.domain.model.EnhancePreset
import com.fotojelas.pro.domain.model.EnhanceRequest
import com.fotojelas.pro.domain.model.EnhanceResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class LocalEnhanceEngine(private val context: Context) {

    private val tflite = TfliteEnhancer(context)

    suspend fun enhance(
        source: android.graphics.Bitmap,
        request: EnhanceRequest,
        onProgress: (Float, String) -> Unit,
    ): EnhanceResult = withContext(Dispatchers.Default) {
        onProgress(0.05f, "Menyiapkan piksel…")
        val working = com.fotojelas.pro.util.ImageLoader.copySoftwareBitmap(source)

        when (request.preset) {
            EnhancePreset.NATURAL -> {
                applyFastPipeline(working, request, 0.35f, 0.22f, 0.18f, onProgress)
            }
            EnhancePreset.JELAS -> {
                applyFastPipeline(working, request, 0.55f, 0.28f, 0.22f, onProgress)
            }
            EnhancePreset.PORTRAIT -> {
                LocalPixelProcessor.luminanceContrast(working, 0.12f, 0.03f)
                LocalPixelProcessor.naturalClarity(working, 0.18f)
                ConvolutionSharpen.apply(working, request.sharpness * 0.65f, { p ->
                    onProgress(0.2f + p * 0.5f, "Portrait — ketajaman wajah…")
                })
                LocalPixelProcessor.denoise(working, 0.35f)
            }
            EnhancePreset.DENOISE -> {
                LocalPixelProcessor.denoise(working, 0.65f)
                ConvolutionSharpen.apply(working, request.sharpness * 0.5f, { p ->
                    onProgress(0.3f + p * 0.4f, "Finishing ketajaman…")
                })
            }
            EnhancePreset.PRO_BLUR -> {
                applyProPipeline(working, request, deblur = 0.32f, onProgress)
            }
            EnhancePreset.DOCUMENT -> {
                LocalPixelProcessor.luminanceContrast(working, 0.38f, 0.08f)
                ConvolutionSharpen.apply(working, 0.72f, { p ->
                    onProgress(0.2f + p * 0.5f, "Ketajaman dokumen…")
                })
            }
            EnhancePreset.UPSCALE_2X -> {
                onProgress(0.2f, "AI lokal 2×…")
                val enhanced = tflite.enhance(working, scale = 2)
                working.recycle()
                ConvolutionSharpen.apply(enhanced, request.sharpness * 0.4f)
                return@withContext EnhanceResult(
                    bitmap = enhanced,
                    engineUsed = if (tflite.hasModel()) EnhanceEngine.TFLITE else EnhanceEngine.LOCAL,
                    outputWidth = enhanced.width,
                    outputHeight = enhanced.height,
                )
            }
            EnhancePreset.AI_4X -> {
                onProgress(0.2f, "AI lokal 4× (2× + 2×)…")
                val step1 = tflite.enhance(working, scale = 2)
                working.recycle()
                val step2 = tflite.enhance(step1, scale = 2)
                step1.recycle()
                ConvolutionSharpen.apply(step2, request.sharpness * 0.35f)
                return@withContext EnhanceResult(
                    bitmap = step2,
                    engineUsed = EnhanceEngine.TFLITE,
                    outputWidth = step2.width,
                    outputHeight = step2.height,
                )
            }
            EnhancePreset.ULTRA_8X -> {
                onProgress(0.15f, "Ultra lokal 8×…")
                var current = working
                repeat(3) { i ->
                    val next = tflite.enhance(current, scale = 2)
                    if (i > 0) current.recycle()
                    current = next
                    onProgress(0.2f + i * 0.2f, "Upscale tahap ${i + 1}/3…")
                }
                working.recycle()
                ConvolutionSharpen.apply(current, request.sharpness * 0.3f)
                return@withContext EnhanceResult(
                    bitmap = current,
                    engineUsed = EnhanceEngine.TFLITE,
                    outputWidth = current.width,
                    outputHeight = current.height,
                )
            }
            EnhancePreset.CLOUD_4X, EnhancePreset.CLOUD_8X -> {
                throw IllegalStateException("Cloud preset harus diproses oleh orchestrator")
            }
        }

        onProgress(0.95f, "Selesai!")
        EnhanceResult(
            bitmap = working,
            engineUsed = EnhanceEngine.LOCAL,
            outputWidth = working.width,
            outputHeight = working.height,
        )
    }

    private suspend fun applyFastPipeline(
        working: android.graphics.Bitmap,
        request: EnhanceRequest,
        sharpness: Float,
        clarity: Float,
        contrast: Float,
        onProgress: (Float, String) -> Unit,
    ) {
        LocalPixelProcessor.luminanceContrast(working, contrast, 0f)
        LocalPixelProcessor.naturalClarity(working, clarity)
        ConvolutionSharpen.apply(working, sharpness, { p ->
            onProgress(0.15f + p * 0.7f, "Konvolusi ketajaman 3×3…")
        })
    }

    private suspend fun applyProPipeline(
        working: android.graphics.Bitmap,
        request: EnhanceRequest,
        deblur: Float,
        onProgress: (Float, String) -> Unit,
    ) {
        applyFastPipeline(working, request, request.sharpness * 0.85f, 0.32f, 0.22f, onProgress)
        LocalPixelProcessor.denoise(working, deblur)
        ConvolutionSharpen.apply(working, request.sharpness * 0.45f, { p ->
            onProgress(0.75f + p * 0.15f, "Deblur Pro…")
        })
    }
}
