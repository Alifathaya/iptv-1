package com.jelasin.enhancer.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun ScanningLineOverlay(
    message: String,
    modifier: Modifier = Modifier,
) {
    val transition = rememberInfiniteTransition(label = "scan")
    val offset by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "scanY",
    )

    Box(modifier = modifier.fillMaxSize()) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val y = size.height * offset
            drawRect(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color(0x406366F1),
                        Color(0x80A855F7),
                        Color.Transparent,
                    ),
                    startY = y - 40f,
                    endY = y + 40f,
                ),
                topLeft = Offset(0f, y - 40f),
                size = androidx.compose.ui.geometry.Size(size.width, 80f),
            )
            drawLine(
                brush = Brush.horizontalGradient(
                    listOf(Color.Transparent, Color(0xFF67E8F9), Color.Transparent),
                ),
                start = Offset(0f, y),
                end = Offset(size.width, y),
                strokeWidth = 2f,
            )
        }
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = Color(0xFF67E8F9),
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(48.dp),
        )
    }
}
