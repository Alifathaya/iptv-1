package com.jelasin.enhancer.ml

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.tensorflow.lite.Interpreter
import kotlin.math.min

/**
 * TensorFlow Lite on-device enhancer.
 * Jika model `enhance_sr.tflite` ada di assets, jalankan inferensi neural.
 * Fallback: bicubic upscale + edge-aware luminance boost (SRCNN-style ringan).
 */
class TfliteEnhancer(private val context: Context) {

    private var interpreter: Interpreter? = null
    private val modelLoaded: Boolean

    init {
        interpreter = try {
            val asset = context.assets.openFd("enhance_sr.tflite")
            val buffer = FileInputStream(asset.fileDescriptor).channel.map(
                java.nio.channels.FileChannel.MapMode.READ_ONLY,
                asset.startOffset,
                asset.declaredLength,
            )
            Interpreter(buffer)
        } catch (_: Exception) {
            null
        }
        modelLoaded = interpreter != null
    }

    fun hasModel(): Boolean = modelLoaded

    fun enhance(bitmap: Bitmap, scale: Int = 2): Bitmap {
        val interp = interpreter
        if (interp == null) return enhanceFallback(bitmap, scale)

        val inputSize = 128
        val small = Bitmap.createScaledBitmap(bitmap, inputSize, inputSize, true)
        val inputBuffer = ByteBuffer.allocateDirect(4 * inputSize * inputSize * 3).apply {
            order(ByteOrder.nativeOrder())
        }
        for (y in 0 until inputSize) {
            for (x in 0 until inputSize) {
                val c = small.getPixel(x, y)
                inputBuffer.putFloat(Color.red(c) / 255f)
                inputBuffer.putFloat(Color.green(c) / 255f)
                inputBuffer.putFloat(Color.blue(c) / 255f)
            }
        }
        inputBuffer.rewind()

        val outSize = inputSize * scale
        val outputBuffer = ByteBuffer.allocateDirect(4 * outSize * outSize * 3).apply {
            order(ByteOrder.nativeOrder())
        }

        try {
            interp.run(inputBuffer, outputBuffer)
        } catch (_: Exception) {
            small.recycle()
            return enhanceFallback(bitmap, scale)
        }

        val result = Bitmap.createBitmap(outSize, outSize, Bitmap.Config.ARGB_8888)
        outputBuffer.rewind()
        for (y in 0 until outSize) {
            for (x in 0 until outSize) {
                val r = min(255, (outputBuffer.float * 255f).toInt())
                val g = min(255, (outputBuffer.float * 255f).toInt())
                val b = min(255, (outputBuffer.float * 255f).toInt())
                result.setPixel(x, y, Color.rgb(r, g, b))
            }
        }
        small.recycle()

        if (scale > 1) {
            val targetW = bitmap.width * scale
            val targetH = bitmap.height * scale
            val scaled = Bitmap.createScaledBitmap(result, targetW, targetH, true)
            result.recycle()
            return scaled
        }
        return result
    }

    /** Fallback neural-style reconstruction tanpa model file */
    fun enhanceFallback(bitmap: Bitmap, scale: Int): Bitmap {
        val up = Bitmap.createScaledBitmap(bitmap, bitmap.width * scale, bitmap.height * scale, true)
        val w = up.width
        val h = up.height
        val pixels = IntArray(w * h)
        up.getPixels(pixels, 0, w, 0, 0, w, h)

        for (y in 1 until h - 1) {
            for (x in 1 until w - 1) {
                val i = y * w + x
                val r = Color.red(pixels[i])
                val g = Color.green(pixels[i])
                val b = Color.blue(pixels[i])
                val lum = 0.299f * r + 0.587f * g + 0.114f * b

                val rN = Color.red(pixels[i - w])
                val rS = Color.red(pixels[i + w])
                val rW = Color.red(pixels[i - 1])
                val rE = Color.red(pixels[i + 1])
                val edge = kotlin.math.abs(r - (rN + rS + rW + rE) / 4f) / 255f

                val boost = 1f + edge * 0.15f
                pixels[i] = Color.rgb(
                    min(255, (r * boost).toInt()),
                    min(255, (g * boost).toInt()),
                    min(255, (b * boost).toInt()),
                )
                if (lum < 1f) continue
            }
        }
        up.setPixels(pixels, 0, w, 0, 0, w, h)
        return up
    }
}
