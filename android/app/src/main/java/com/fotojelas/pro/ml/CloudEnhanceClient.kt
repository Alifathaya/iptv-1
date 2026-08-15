package com.fotojelas.pro.ml

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import com.fotojelas.pro.domain.model.EnhanceEngine
import com.fotojelas.pro.domain.model.EnhanceRequest
import com.fotojelas.pro.domain.model.EnhanceResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.TimeUnit

/** Klien Cloud GPU — Real-ESRGAN via FastAPI backend */
class CloudEnhanceClient {

    private val client = OkHttpClient.Builder()
        .connectTimeout(120, TimeUnit.SECONDS)
        .readTimeout(300, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .build()

    suspend fun enhance(
        source: Bitmap,
        request: EnhanceRequest,
        scale: Int,
        onProgress: (Float, String) -> Unit,
    ): EnhanceResult = withContext(Dispatchers.IO) {
        val baseUrl = request.cloudApiUrl.trim().removeSuffix("/")
        if (baseUrl.isBlank()) {
            throw IllegalArgumentException("URL server Cloud AI belum diatur")
        }

        onProgress(0.1f, "Mengirim ke GPU cloud…")

        val tempFile = File.createTempFile("fotojelas_upload", ".jpg")
        try {
            ByteArrayOutputStream().use { bos ->
                source.compress(Bitmap.CompressFormat.JPEG, 92, bos)
                tempFile.writeBytes(bos.toByteArray())
            }

            val body = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart(
                    "image",
                    "photo.jpg",
                    tempFile.asRequestBody("image/jpeg".toMediaType()),
                )
                .addFormDataPart("scale", scale.toString())
                .addFormDataPart("deblur", "25")
                .addFormDataPart("sharpness", (request.sharpness * 100).toInt().toString())
                .addFormDataPart("contrast", "22")
                .build()

            val requestBuilder = Request.Builder()
                .url("$baseUrl/v1/enhance")
                .post(body)

            if (request.cloudApiKey.isNotBlank()) {
                requestBuilder.addHeader("X-API-Key", request.cloudApiKey)
            }

            onProgress(0.35f, "AI sedang menganalisis dan merekonstruksi piksel…")

            val response = client.newCall(requestBuilder.build()).execute()
            if (!response.isSuccessful) {
                throw IllegalStateException("Cloud API error: ${response.code} ${response.message}")
            }

            val bytes = response.body?.bytes()
                ?: throw IllegalStateException("Respons cloud kosong")

            onProgress(0.85f, "Mendekode hasil HD…")

            val result = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                ?: throw IllegalStateException("Gagal mendekode gambar dari cloud")

            onProgress(1f, "Selesai!")
            EnhanceResult(
                bitmap = result,
                engineUsed = EnhanceEngine.CLOUD,
                outputWidth = result.width,
                outputHeight = result.height,
            )
        } finally {
            tempFile.delete()
        }
    }

    suspend fun healthCheck(apiUrl: String, apiKey: String): Boolean = withContext(Dispatchers.IO) {
        val base = apiUrl.trim().removeSuffix("/")
        if (base.isBlank()) return@withContext false
        try {
            val builder = Request.Builder().url("$base/health").get()
            if (apiKey.isNotBlank()) builder.addHeader("X-API-Key", apiKey)
            client.newCall(builder.build()).execute().isSuccessful
        } catch (_: Exception) {
            false
        }
    }
}
