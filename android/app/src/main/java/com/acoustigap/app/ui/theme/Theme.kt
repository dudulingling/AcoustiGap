package com.acoustigap.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val BlackBg = Color(0xFF121212)
val CardDark = Color(0xFF181818)
val CardElevated = Color(0xFF202020)
val InputBg = Color(0xFF141414)
val BorderSubtle = Color(0xFF282828)
val BorderStrong = Color(0xFF383838)

val TextPrimary = Color(0xFFF5F5F5)
val TextSecondary = Color(0xFF8E8E8E)
val TextTertiary = Color(0xFF666666)

val AccentSilver = Color(0xFFE0E0E0)
val SuccessGreen = Color(0xFF4ADE80)
val SuccessBg = Color(0xFF064E3B)
val WarningAmber = Color(0xFFFBBF24)
val WarningBg = Color(0xFF78350F)
val ErrorRed = Color(0xFFEF4444)
val ErrorBg = Color(0xFF7F1D1D)

private val AcoustiGapColorScheme = darkColorScheme(
    primary = AccentSilver,
    onPrimary = Color(0xFF121212),
    primaryContainer = Color(0xFF2A2A2A),
    onPrimaryContainer = Color(0xFFEDEDED),
    secondary = Color(0xFF9E9E9E),
    onSecondary = Color(0xFF121212),
    background = BlackBg,
    onBackground = TextPrimary,
    surface = CardDark,
    onSurface = TextPrimary,
    surfaceVariant = CardElevated,
    onSurfaceVariant = TextSecondary,
    outline = BorderSubtle,
    outlineVariant = BorderStrong,
    error = ErrorRed,
    onError = Color.White
)

@Composable
fun AcoustiGapTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AcoustiGapColorScheme,
        content = content
    )
}
