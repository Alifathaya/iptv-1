package com.fotojelas.pro.ml

import android.graphics.Bitmap
import android.graphics.Color
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Pemrosesan piksel lokal — luminance, denoise, upscale bicubic + sharpen */
object LocalPixelProcessor {

    suspend fun denoise(bitmap: Bitmap, amount: Float) = withContext(Dispatchers.Default) {
        if (amount <= 0f) return@withContext
        val w = bitmap.width
        val h = bitmap.height
        val pixels = IntArray(w * h)
        bitmap.getPixels(pixels, 0, w, 0, 0, w, h)
        val copy = pixels.copyOf()
        val blend = min(0.45f, amount * 0.45f)
        val threshold = 6f + amount * 20f

        for (y in 1 until h - 1) {
            for (x in 1 until w - 1) {
                val i = y * w + x
                var rSum = 0
                var gSum = 0
                var bSum = 0
                var count = 0
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        val j = (y + dy) * w + (x + dx)
                        rSum += Color.red(copy[j])
                        gSum += Color.green(copy[j])
                        bSum += Color.blue(copy[j])
                        count++
                    }
                }
                val rB = rSum / count
                val gB = gSum / count
                val bB = bSum / count
                val r = Color.red(copy[i])
                val g = Color.green(copy[i])
                val b = Color.blue(copy[i])
                val diff = kotlin.math.sqrt(
                    (r - rB).toDouble().pow(2) +
                        (g - gB).toDouble().pow(2) +
                        (b - bB).toDouble().pow(2)
                ).toFloat()

                if (diff < threshold) {
                    val nr = (r * (1 - blend) + rB * blend).toInt()
                    val ng = (g * (1 - blend) + gB * blend).toInt()
                    val nb = (b * (1 - blend) + bB * blend).toInt()
                    pixels[i] = Color.rgb(nr, ng, nb)
                }
            }
        }
        bitmap.setPixels(pixels, 0, w, 0, 0, w, h)
    }

    suspend fun luminanceContrast(bitmap: Bitmap, contrast: Float, brightness: Float) =
        withContext(Dispatchers.Default) {
            val w = bitmap.width
            val h = bitmap.height
            val pixels = IntArray(w * h)
            bitmap.getPixels(pixels, 0, w, 0, 0, w, h)
            val c = contrast * 0.9f
            val factor = if (c == 0f) 1f else (259f * (c + 255f)) / (255f * (259f - c))
            val b = brightness * 2.55f

            for (i in pixels.indices) {
                val r = Color.red(pixels[i])
                val g = Color.green(pixels[i])
                val bCh = Color.blue(pixels[i])
                val lum = 0.299f * r + 0.587f * g + 0.114f * bCh
                var newLum = lum + b
                if (c != 0f) newLum = factor * (newLum - 128f) + 128f
                newLum = min(255f, max(0f, newLum))
                if (lum > 1f) {
                    val scale = newLum / lum
                    pixels[i] = Color.rgb(
                        clamp((r * scale).toInt()),
                        clamp((g * scale).toInt()),
                        clamp((bCh * scale).toInt()),
                    )
                }
            }
            bitmap.setPixels(pixels, 0, w, 0, 0, w, h)
        }

    suspend fun naturalClarity(bitmap: Bitmap, amount: Float) = withContext(Dispatchers.Default) {
        if (amount <= 0f) return@withContext
        val w = bitmap.width
        val h = bitmap.height
        val radius = 7
        val pixels = IntArray(w * h)
        bitmap.getPixels(pixels, 0, w, 0, 0, w, h)
        val blurred = boxBlur(pixels, w, h, radius)
        val strength = amount * 0.28f

        for (i in pixels.indices) {
            val r = Color.red(pixels[i])
            val g = Color.green(pixels[i])
            val b = Color.blue(pixels[i])
            val lum = 0.299f * r + 0.587f * g + 0.114f * b
            val lumB = 0.299f * Color.red(blurred[i]) + 0.587f * Color.green(blurred[i]) +
                0.114f * Color.blue(blurred[i])
            val midWeight = 1f - abs(lum - 128f).pow(1.4f) / 128f.pow(1.4f)
            val detail = (lum - lumB) * strength * midWeight
            if (lum > 1f && abs(detail) > 0.2f) {
                val scale = (lum + detail) / lum
                pixels[i] = Color.rgb(
                    clamp((r * scale).toInt()),
                    clamp((g * scale).toInt()),
                    clamp((b * scale).toInt()),
                )
            }
        }
        bitmap.setPixels(pixels, 0, w, 0, 0, w, h)
    }

    fun upscale(bitmap: Bitmap, scale: Int): Bitmap {
        val nw = bitmap.width * scale
        val nh = bitmap.height * scale
        return Bitmap.createScaledBitmap(bitmap, nw, nh, true)
    }

    private fun boxBlur(pixels: IntArray, w: Int, h: Int, radius: Int): IntArray {
        val out = IntArray(pixels.size)
        for (y in 0 until h) {
            for (x in 0 until w) {
                var rSum = 0
                var gSum = 0
                var bSum = 0
                var count = 0
                for (dy in -radius..radius) {
                    for (dx in -radius..radius) {
                        val ny = min(h - 1, max(0, y + dy))
                        val nx = min(w - 1, max(0, x + dx))
                        val j = ny * w + nx
                        rSum += Color.red(pixels[j])
                        gSum += Color.green(pixels[j])
                        bSum += Color.blue(pixels[j])
                        count++
                    }
                }
                out[y * w + x] = Color.rgb(rSum / count, gSum / count, bSum / count)
            }
        }
        return out
    }

    private fun clamp(v: Int) = min(255, max(0, v))
}
