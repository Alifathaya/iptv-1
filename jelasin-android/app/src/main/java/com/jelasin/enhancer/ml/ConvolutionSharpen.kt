package com.jelasin.enhancer.ml

import android.graphics.Bitmap
import android.graphics.Color
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.coroutines.yield

/**
 * Konvolusi ketajaman matriks 3×3 Laplacian (sum = 1).
 * Diproses per-batch baris di [Dispatchers.Default] — padanan coroutine background.
 */
object ConvolutionSharpen {

    private const val ROW_BATCH = 48

    suspend fun apply(bitmap: Bitmap, strength: Float, onProgress: (Float) -> Unit = {}) {
        if (strength <= 0f) return
        withContext(Dispatchers.Default) {
            val s = min(0.22f, max(0f, strength * 0.22f))
            val center = 1f + 4f * s
            val w = bitmap.width
            val h = bitmap.height
            val pixels = IntArray(w * h)
            bitmap.getPixels(pixels, 0, w, 0, 0, w, h)
            val copy = pixels.copyOf()
            val innerRows = h - 2
            var processed = 0

            for (yStart in 1 until h - 1 step ROW_BATCH) {
                val yEnd = min(h - 1, yStart + ROW_BATCH)
                for (y in yStart until yEnd) {
                    for (x in 1 until w - 1) {
                        val i = y * w + x
                        val iN = i - w
                        val iS = i + w
                        val iW = i - 1
                        val iE = i + 1

                        val r = Color.red(copy[i])
                        val g = Color.green(copy[i])
                        val b = Color.blue(copy[i])

                        val rW = Color.red(copy[iW])
                        val rE = Color.red(copy[iE])
                        val rN = Color.red(copy[iN])
                        val rS = Color.red(copy[iS])

                        val gW = Color.green(copy[iW])
                        val gE = Color.green(copy[iE])
                        val gN = Color.green(copy[iN])
                        val gS = Color.green(copy[iS])

                        val bW = Color.blue(copy[iW])
                        val bE = Color.blue(copy[iE])
                        val bN = Color.blue(copy[iN])
                        val bS = Color.blue(copy[iS])

                        val nr = clamp((r * center - rW * s - rE * s - rN * s - rS * s).toInt())
                        val ng = clamp((g * center - gW * s - gE * s - gN * s - gS * s).toInt())
                        val nb = clamp((b * center - bW * s - bE * s - bN * s - bS * s).toInt())

                        pixels[i] = Color.rgb(nr, ng, nb)
                    }
                }
                processed += yEnd - yStart
                if (innerRows > 0) {
                    onProgress(processed.toFloat() / innerRows)
                }
                yield()
                delay(1)
            }

            bitmap.setPixels(pixels, 0, w, 0, 0, w, h)
        }
    }

    private fun clamp(v: Int) = min(255, max(0, v))
}
