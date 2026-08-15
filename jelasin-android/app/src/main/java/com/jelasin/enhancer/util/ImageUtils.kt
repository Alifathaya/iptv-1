package com.jelasin.enhancer.util

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

object ImageLoader {

    private const val MAX_DIMENSION = 3072

    suspend fun decodeFromUri(context: Context, uri: Uri): Bitmap = withContext(Dispatchers.IO) {
        val source = ImageDecoder.createSource(context.contentResolver, uri)
        ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
            decoder.isMutableRequired = true
            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            val maxSide = maxOf(info.size.width, info.size.height)
            if (maxSide > MAX_DIMENSION) {
                val scale = MAX_DIMENSION.toFloat() / maxSide.toFloat()
                decoder.setTargetSize(
                    (info.size.width * scale).toInt(),
                    (info.size.height * scale).toInt(),
                )
            }
        }
    }

    fun copySoftwareBitmap(source: Bitmap): Bitmap {
        val copy = Bitmap.createBitmap(source.width, source.height, Bitmap.Config.ARGB_8888)
        val canvas = android.graphics.Canvas(copy)
        canvas.drawBitmap(source, 0f, 0f, null)
        return copy
    }

    suspend fun saveToCache(context: Context, bitmap: Bitmap, prefix: String): String =
        withContext(Dispatchers.IO) {
            val file = File(context.cacheDir, "${prefix}_${System.currentTimeMillis()}.png")
            FileOutputStream(file).use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }
            file.absolutePath
        }
}

object MediaStoreSaver {

    suspend fun saveToGallery(context: Context, bitmap: Bitmap, displayName: String): Uri =
        withContext(Dispatchers.IO) {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, displayName)
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(
                        MediaStore.Images.Media.RELATIVE_PATH,
                        Environment.DIRECTORY_PICTURES + "/Jelasin",
                    )
                    put(MediaStore.Images.Media.IS_PENDING, 1)
                }
            }

            val resolver = context.contentResolver
            val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: throw IllegalStateException("Gagal membuat entri MediaStore")

            resolver.openOutputStream(uri)?.use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            } ?: throw IllegalStateException("Gagal membuka stream galeri")

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                values.clear()
                values.put(MediaStore.Images.Media.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            }

            uri
        }
}

object BlurDetector {

    /** Laplacian variance — nilai rendah = gambar buram / goyang */
    fun varianceOfLaplacian(bitmap: Bitmap): Double {
        val small = Bitmap.createScaledBitmap(bitmap, 320, 240, true)
        val w = small.width
        val h = small.height
        val pixels = IntArray(w * h)
        small.getPixels(pixels, 0, w, 0, 0, w, h)
        small.recycle()

        var sum = 0.0
        var sumSq = 0.0
        var count = 0

        for (y in 1 until h - 1) {
            for (x in 1 until w - 1) {
                val i = y * w + x
                val c = pixels[i]
                val lum = (android.graphics.Color.red(c) + android.graphics.Color.green(c) +
                    android.graphics.Color.blue(c)) / 3.0
                val lumN = (android.graphics.Color.red(pixels[i - w]) +
                    android.graphics.Color.green(pixels[i - w]) +
                    android.graphics.Color.blue(pixels[i - w])) / 3.0
                val lumS = (android.graphics.Color.red(pixels[i + w]) +
                    android.graphics.Color.green(pixels[i + w]) +
                    android.graphics.Color.blue(pixels[i + w])) / 3.0
                val lumW = (android.graphics.Color.red(pixels[i - 1]) +
                    android.graphics.Color.green(pixels[i - 1]) +
                    android.graphics.Color.blue(pixels[i - 1])) / 3.0
                val lumE = (android.graphics.Color.red(pixels[i + 1]) +
                    android.graphics.Color.green(pixels[i + 1]) +
                    android.graphics.Color.blue(pixels[i + 1])) / 3.0
                val lap = 4 * lum - lumN - lumS - lumW - lumE
                sum += lap
                sumSq += lap * lap
                count++
            }
        }

        if (count == 0) return 0.0
        val mean = sum / count
        return sumSq / count - mean * mean
    }

    fun isBlurry(bitmap: Bitmap, threshold: Double = 80.0): Boolean =
        varianceOfLaplacian(bitmap) < threshold
}
