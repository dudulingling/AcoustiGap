package com.acoustigap.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.acoustigap.app.dsp.DspEngine
import com.acoustigap.app.ui.components.SpectrogramView
import com.acoustigap.app.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun DiagnosticsScreen(
    dspEngine: DspEngine,
    audioLevels: List<Float>,
    currentRmsDb: Float,
    captureBufferProvider: () -> ShortArray
) {
    val scope = rememberCoroutineScope()
    var isTesting by remember { mutableStateOf(false) }
    var testProgress by remember { mutableStateOf(0f) }
    var diagnosticResult by remember { mutableStateOf<DspEngine.NoiseProfile?>(null) }
    var statusText by remember { mutableStateOf("Ready to evaluate ambient room noise & channel health.") }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BlackBg)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- 1. Real-Time Waterfall Spectrogram ---
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = CardDark),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BorderSubtle, RoundedCornerShape(10.dp))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "🔬 Live Acoustic Spectrum",
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary,
                            fontSize = 15.sp
                        )
                        Text(
                            text = "Level: ${"%.1f".format(currentRmsDb)} dBFS",
                            color = if (currentRmsDb > -30f) WarningAmber else SuccessGreen,
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    SpectrogramView(audioLevels = audioLevels)
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Frequency range: 0 Hz — 24,000 Hz (Nyquist @ 48 kHz)",
                        color = TextTertiary,
                        fontSize = 11.sp
                    )
                }
            }
        }

        // --- 2. Channel Diagnostics Assessment ---
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = CardDark),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BorderSubtle, RoundedCornerShape(10.dp))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "📊 Channel Diagnostics & SNR Assessment",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    Button(
                        onClick = {
                            if (!isTesting) {
                                isTesting = true
                                testProgress = 0f
                                statusText = "Sampling live microphone sound for 1.5 seconds..."

                                scope.launch {
                                    val collectedSamples = mutableListOf<Short>()
                                    val startTime = System.currentTimeMillis()

                                    while (System.currentTimeMillis() - startTime < 1500) {
                                        val frame = captureBufferProvider()
                                        for (s in frame) collectedSamples.add(s)
                                        testProgress = ((System.currentTimeMillis() - startTime) / 1500f).coerceIn(0f, 1f)
                                        delay(100)
                                    }

                                    val samplesArray = ShortArray(collectedSamples.size) { collectedSamples[it] }
                                    diagnosticResult = dspEngine.analyzeNoise(samplesArray)
                                    isTesting = false
                                    statusText = "Assessment complete."
                                }
                            }
                        },
                        enabled = !isTesting,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF282828),
                            contentColor = TextPrimary
                        ),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (isTesting) "Measuring Noise Floor..." else "⚡ Test Noise Floor & SNR (Sample 1.5s)")
                    }

                    if (isTesting) {
                        Spacer(modifier = Modifier.height(10.dp))
                        LinearProgressIndicator(
                            progress = { testProgress },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(6.dp),
                            color = AccentSilver,
                            trackColor = Color(0xFF202020)
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = statusText, color = TextSecondary, fontSize = 12.sp)

                    // Results Box
                    diagnosticResult?.let { res ->
                        Spacer(modifier = Modifier.height(14.dp))
                        Surface(
                            color = InputBg,
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, BorderSubtle, RoundedCornerShape(8.dp))
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(
                                    text = "Channel Diagnostic Report",
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary,
                                    fontSize = 14.sp
                                )
                                Spacer(modifier = Modifier.height(8.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text("RMS Noise Floor:", color = TextSecondary, fontSize = 13.sp)
                                    Text("${"%.2f".format(res.rmsDb)} dBFS", color = SuccessGreen, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                }
                                Spacer(modifier = Modifier.height(4.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text("Peak Noise Level:", color = TextSecondary, fontSize = 13.sp)
                                    Text("${"%.2f".format(res.peakDb)} dBFS", color = WarningAmber, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                }
                                Spacer(modifier = Modifier.height(4.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text("Channel Health:", color = TextSecondary, fontSize = 13.sp)
                                    Text(res.health, color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                HorizontalDivider(color = Color(0xFF282828))
                                Spacer(modifier = Modifier.height(8.dp))

                                Text("Recommendation:", color = TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                Text(res.recommendation, color = Color(0xFFCCCCCC), fontSize = 12.sp)

                                if (res.topFreqs.isNotEmpty()) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text("Top Noise Frequencies:", color = TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                    res.topFreqs.take(4).forEach { (f, db) ->
                                        Text(
                                            "• ${f.toInt()} Hz: ${"%.1f".format(db)} dB",
                                            color = Color(0xFFB0B0B0),
                                            fontSize = 11.sp
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
