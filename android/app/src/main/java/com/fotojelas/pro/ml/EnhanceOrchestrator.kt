package com.fotojelas.pro.ml

import android.content.Context
import android.graphics.Bitmap
import com.fotojelas.pro.domain.model.EnhancePreset
import com.fotojelas.pro.domain.model.EnhanceRequest
import com.fotojelas.pro.domain.model.EnhanceResult

/** Orkestrasi: lokal + TFLite + Cloud GPU (gabungan Foto Jelas Pro + Jelasin) */
class EnhanceOrchestrator(context: Context) {

    private val local = LocalEnhanceEngine(context)
    private val cloud = CloudEnhanceClient()

    suspend fun enhance(
        source: Bitmap,
        request: EnhanceRequest,
        onProgress: (Float, String) -> Unit,
    ): EnhanceResult {
        return when (request.preset) {
            EnhancePreset.CLOUD_8X, EnhancePreset.ULTRA_8X ->
                cloudWithFallback(source, request, scale = 8, onProgress)

            EnhancePreset.CLOUD_4X, EnhancePreset.AI_4X ->
                cloudWithFallback(source, request, scale = 4, onProgress)

            else -> local.enhance(source, request, onProgress)
        }
    }

    private suspend fun cloudWithFallback(
        source: Bitmap,
        request: EnhanceRequest,
        scale: Int,
        onProgress: (Float, String) -> Unit,
    ): EnhanceResult {
        if (request.cloudApiUrl.isNotBlank()) {
            try {
                return cloud.enhance(source, request, scale, onProgress)
            } catch (e: Exception) {
                onProgress(0.15f, "Cloud gagal — mode lokal…")
            }
        }
        val fallbackPreset = when (scale) {
            8 -> EnhancePreset.ULTRA_8X
            else -> EnhancePreset.AI_4X
        }
        return local.enhance(
            source,
            request.copy(preset = fallbackPreset),
            onProgress,
        )
    }

    suspend fun checkCloud(url: String, key: String): Boolean = cloud.healthCheck(url, key)
}
