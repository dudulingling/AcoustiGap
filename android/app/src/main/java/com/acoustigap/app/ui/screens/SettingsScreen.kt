package com.acoustigap.app.ui.screens

import android.os.Build
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.acoustigap.app.ui.theme.*

@Composable
fun SettingsScreen() {
    var rawMicEnabled by remember { mutableStateOf(true) }
    var hapticFeedbackEnabled by remember { mutableStateOf(true) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BlackBg)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- 1. Samsung S24 Ultra Hardware Optimizations ---
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
                        text = "📱 Samsung Galaxy S24 Ultra Tuning",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Bypass One UI Voice Focus (UNPROCESSED)",
                                color = TextPrimary,
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 13.sp
                            )
                            Text(
                                text = "Bypasses beamforming & noise cancellation so ultrasound (15-20 kHz) is captured with full dynamic range.",
                                color = TextSecondary,
                                fontSize = 11.sp
                            )
                        }
                        Switch(
                            checked = rawMicEnabled,
                            onCheckedChange = { rawMicEnabled = it },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = TextPrimary,
                                checkedTrackColor = Color(0xFF383838),
                                uncheckedThumbColor = TextSecondary,
                                uncheckedTrackColor = InputBg
                            )
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    HorizontalDivider(color = Color(0xFF282828))
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Haptic Vibration on Packet",
                                color = TextPrimary,
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 13.sp
                            )
                            Text(
                                text = "Vibrate briefly when an acoustic frame CRC32 is successfully verified.",
                                color = TextSecondary,
                                fontSize = 11.sp
                            )
                        }
                        Switch(
                            checked = hapticFeedbackEnabled,
                            onCheckedChange = { hapticFeedbackEnabled = it },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = TextPrimary,
                                checkedTrackColor = Color(0xFF383838),
                                uncheckedThumbColor = TextSecondary,
                                uncheckedTrackColor = InputBg
                            )
                        )
                    }
                }
            }
        }

        // --- 2. Audio Engine Configuration ---
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
                        text = "🔊 Audio Engine Parameters",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    Text("• Sample Rate: 48,000 Hz PCM Mono (Nyquist: 24,000 Hz)", color = TextSecondary, fontSize = 12.sp)
                    Text("• PCM Format: ENCODING_PCM_16BIT signed little-endian", color = TextSecondary, fontSize = 12.sp)
                    Text("• Frame Header: 15-byte IEEE 802.3 CRC32 big-endian", color = TextSecondary, fontSize = 12.sp)
                    Text("• Binary Bridge: Base85 '!B85:' envelope encapsulation", color = TextSecondary, fontSize = 12.sp)
                    Text("• Target Device: ${Build.MANUFACTURER} ${Build.MODEL} (Android ${Build.VERSION.RELEASE})", color = TextSecondary, fontSize = 12.sp)
                }
            }
        }

        // --- 3. Air-Gap Interoperability Guide ---
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
                        text = "💡 Windows Interoperability Notes",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = "1. Chế độ Siêu âm (Ultrasound): Chọn 'ULTRASOUND_FAST' trên cả Windows và Android để truyền tin hoàn toàn im lặng.\n" +
                                "2. Khoảng cách: Đặt điện thoại cách loa/mic máy tính từ 10cm - 50cm để đạt SNR tốt nhất.\n" +
                                "3. Dell G5 / PC: Tắt Waves MaxxAudio Pro Noise Reduction trên máy tính để tránh làm mờ dải tần số 15-20 kHz.",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        lineHeight = 18.sp
                    )
                }
            }
        }
    }
}
