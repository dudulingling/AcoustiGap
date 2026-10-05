package com.acoustigap.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.acoustigap.app.ui.theme.BorderSubtle
import com.acoustigap.app.ui.theme.InputBg

@Composable
fun SpectrogramView(
    audioLevels: List<Float>,
    modifier: Modifier = Modifier
) {
    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(72.dp)
            .background(InputBg, shape = RoundedCornerShape(8.dp))
            .border(1.dp, BorderSubtle, shape = RoundedCornerShape(8.dp))
    ) {
        val width = size.width
        val height = size.height
        val barCount = 48
        val barWidth = width / barCount

        // Draw frequency grid lines
        drawLine(
            color = Color(0xFF242424),
            start = Offset(0f, height * 0.25f),
            end = Offset(width, height * 0.25f),
            strokeWidth = 1f
        )
        drawLine(
            color = Color(0xFF242424),
            start = Offset(0f, height * 0.5f),
            end = Offset(width, height * 0.5f),
            strokeWidth = 1f
        )
        drawLine(
            color = Color(0xFF242424),
            start = Offset(0f, height * 0.75f),
            end = Offset(width, height * 0.75f),
            strokeWidth = 1f
        )

        // Draw dynamic spectral energy bars
        val step = if (audioLevels.isNotEmpty()) maxOf(1, audioLevels.size / barCount) else 1
        for (i in 0 until barCount) {
            val idx = (i * step).coerceAtMost(audioLevels.size - 1)
            val level = if (idx in audioLevels.indices) audioLevels[idx] else 0.05f
            val barHeight = (level.coerceIn(0.02f, 1f) * height)

            val barColor = when {
                level > 0.8f -> Color(0xFFE0E0E0)
                level > 0.4f -> Color(0xFF9E9E9E)
                else -> Color(0xFF505050)
            }

            drawRect(
                color = barColor,
                topLeft = Offset(i * barWidth + (barWidth * 0.15f), height - barHeight),
                size = Size(barWidth * 0.7f, barHeight)
            )
        }
    }
}
