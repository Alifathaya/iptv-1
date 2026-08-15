package com.jelasin.enhancer.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val JelasinDark = darkColorScheme(
    primary = Color(0xFF818CF8),
    onPrimary = Color(0xFF0B1020),
    secondary = Color(0xFFA855F7),
    background = Color(0xFF070B14),
    surface = Color(0xFF12182A),
    onBackground = Color(0xFFF0F4FF),
    onSurface = Color(0xFFF0F4FF),
    surfaceVariant = Color(0xFF1E293B),
)

@Composable
fun JelasinTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = JelasinDark,
        content = content,
    )
}
