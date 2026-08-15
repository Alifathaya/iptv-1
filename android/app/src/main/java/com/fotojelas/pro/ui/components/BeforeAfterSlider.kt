package com.fotojelas.pro.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt

@Composable
fun BeforeAfterSlider(
    before: @Composable () -> Unit,
    after: @Composable () -> Unit,
    position: Float,
    onPositionChange: (Float) -> Unit,
    modifier: Modifier = Modifier,
) {
    val pos = position.coerceIn(0f, 1f)

    BoxWithConstraints(
        modifier = modifier
            .clipToBounds()
            .pointerInput(Unit) {
                detectDragGestures { change, _ ->
                    if (size.width > 0) onPositionChange(change.position.x / size.width)
                }
            },
    ) {
        val clipWidth = maxWidth * pos

        Box(Modifier.fillMaxSize()) { after() }

        Box(
            Modifier
                .width(clipWidth)
                .fillMaxHeight()
                .clipToBounds()
                .align(Alignment.TopStart),
        ) {
            Box(Modifier.width(this@BoxWithConstraints.maxWidth).fillMaxHeight()) { before() }
        }

        val handlePx = (maxWidth.value * pos).roundToInt()
        Canvas(
            modifier = Modifier
                .align(Alignment.TopStart)
                .offset { IntOffset(handlePx, 0) }
                .width(2.dp)
                .fillMaxHeight(),
        ) {
            drawLine(
                color = androidx.compose.ui.graphics.Color(0xFF67E8F9),
                start = androidx.compose.ui.geometry.Offset(0f, 0f),
                end = androidx.compose.ui.geometry.Offset(0f, size.height),
                strokeWidth = 3f,
            )
        }
    }
}
