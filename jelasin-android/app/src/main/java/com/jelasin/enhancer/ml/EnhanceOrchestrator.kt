package com.jelasin.enhancer.ml

import android.content.Context
import android.graphics.Bitmap
import com.jelasin.enhancer.domain.model.EnhancePreset
import com.jelasin.enhancer.domain.model.EnhanceRequest
import com.jelasin.enhancer.domain.model.EnhanceResult

/** Orkestrasi engine lokal, TFLite, dan cloud */
class EnhanceOrchestrator(context: Context) {

    private val local = LocalEnhanceEngine(context)
    private val cloud = CloudEnhanceClient()

    suspend fun enhance(
        source: Bitmap,
        request: EnhanceRequest,
        onProgress: (Float, String) -> Unit,
    ): EnhanceResult {
        return when (request.preset) {
            EnhancePreset.UPSCALE_4X -> {
                try {
                    cloud.enhance(source, request, onProgress)
                } catch (e: Exception) {
                    onProgress(0.2f, "Cloud gagal — fallback lokal 2×…")
                    local.enhance(
                        source,
                        request.copy(preset = EnhancePreset.UPSCALE_2X),
                        onProgress,
                    )
                }
            }
            else -> local.enhance(source, request, onProgress)
        }
    }

    suspend fun checkCloud(url: String, key: String): Boolean = cloud.healthCheck(url, key)
}
