package com.jelasin.enhancer.ml

import android.content.Context
import android.graphics.Bitmap
import com.jelasin.enhancer.domain.model.EnhanceEngine
import com.jelasin.enhancer.domain.model.EnhancePreset
import com.jelasin.enhancer.domain.model.EnhanceRequest
import com.jelasin.enhancer.domain.model.EnhanceResult
import com.jelasin.enhancer.util.ImageLoader
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Engine pemrosesan lokal + TFLite fallback.
 * Pipeline: luminance → clarity → konvolusi 3×3 async → denoise/upscale.
 */
class LocalEnhanceEngine(private val context: Context) {

    private val tflite = TfliteEnhancer(context)

    suspend fun enhance(
        source: Bitmap,
        request: EnhanceRequest,
        onProgress: (Float, String) -> Unit,
    ): EnhanceResult = withContext(Dispatchers.Default) {
        onProgress(0.05f, "Menyiapkan piksel…")
        val working = ImageLoader.copySoftwareBitmap(source)

        when (request.preset) {
            EnhancePreset.NATURAL -> {
                LocalPixelProcessor.luminanceContrast(working, 0.18f, 0f)
                onProgress(0.15f, "Kejelasan lokal…")
                LocalPixelProcessor.naturalClarity(working, 0.22f)
                ConvolutionSharpen.apply(working, request.sharpness, { p ->
                    onProgress(0.15f + p * 0.55f, "Konvolusi ketajaman 3×3…")
                })
            }
            EnhancePreset.FACE -> {
                LocalPixelProcessor.luminanceContrast(working, 0.12f, 0.03f)
                LocalPixelProcessor.naturalClarity(working, 0.18f)
                ConvolutionSharpen.apply(working, request.sharpness * 0.7f, { p ->
                    onProgress(0.2f + p * 0.4f, "Mempertajam detail wajah…")
                })
                LocalPixelProcessor.denoise(working, 0.35f)
            }
            EnhancePreset.DENOISE -> {
                LocalPixelProcessor.denoise(working, 0.65f)
                ConvolutionSharpen.apply(working, request.sharpness * 0.5f, { p ->
                    onProgress(0.3f + p * 0.4f, "Finishing ketajaman…")
                })
            }
            EnhancePreset.UPSCALE_2X -> {
                onProgress(0.2f, "AI lokal merekonstruksi 2×…")
                val enhanced = tflite.enhance(working, scale = 2)
                working.recycle()
                onProgress(0.85f, "Polish akhir…")
                ConvolutionSharpen.apply(enhanced, request.sharpness * 0.4f)
                return@withContext EnhanceResult(
                    bitmap = enhanced,
                    engineUsed = if (tflite.hasModel()) EnhanceEngine.TFLITE else EnhanceEngine.LOCAL,
                    outputWidth = enhanced.width,
                    outputHeight = enhanced.height,
                )
            }
            EnhancePreset.UPSCALE_4X -> {
                throw IllegalStateException("Upscale 4x membutuhkan Cloud AI")
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
}
