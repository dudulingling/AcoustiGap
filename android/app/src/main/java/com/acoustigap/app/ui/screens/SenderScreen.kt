package com.acoustigap.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.acoustigap.app.audio.AudioPlaybackManager
import com.acoustigap.app.dsp.DspEngine
import com.acoustigap.app.dsp.DspProtocol
import com.acoustigap.app.protocol.Base85
import com.acoustigap.app.protocol.FileChunker
import com.acoustigap.app.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun SenderScreen(
    dspEngine: DspEngine,
    playbackManager: AudioPlaybackManager,
    selectedProtocol: DspProtocol,
    onProtocolChanged: (DspProtocol) -> Unit,
    volumePercent: Int,
    onVolumeChanged: (Int) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var messageText by remember { mutableStateOf("") }
    val sentMessages = remember { mutableStateListOf<Pair<String, String>>() }

    // File transfer state
    var selectedFileUri by remember { mutableStateOf<Uri?>(null) }
    var selectedFileName by remember { mutableStateOf<String?>(null) }
    var selectedFileSize by remember { mutableStateOf<Long?>(null) }
    var fileSendProgress by remember { mutableStateOf(0f) }
    var isTransmitting by remember { mutableStateOf(false) }
    var fileLogText by remember { mutableStateOf("Ready to transmit file.") }

    val filePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            selectedFileUri = uri
            val cursor = context.contentResolver.query(uri, null, null, null, null)
            cursor?.use {
                if (it.moveToFirst()) {
                    val nameIdx = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                    val sizeIdx = it.getColumnIndex(android.provider.OpenableColumns.SIZE)
                    if (nameIdx != -1) selectedFileName = it.getString(nameIdx)
                    if (sizeIdx != -1) selectedFileSize = it.getLong(sizeIdx)
                }
            }
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BlackBg)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- 1. Quick Config Card ---
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
                        text = "⚙️ Transmission Settings",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    // Protocol Selector
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf(DspProtocol.FAST, DspProtocol.ULTRASOUND_FAST).forEach { proto ->
                            val isSelected = proto == selectedProtocol
                            Button(
                                onClick = { onProtocolChanged(proto) },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (isSelected) Color(0xFF2B2B2B) else InputBg,
                                    contentColor = if (isSelected) TextPrimary else TextSecondary
                                ),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier
                                    .weight(1f)
                                    .border(
                                        1.dp,
                                        if (isSelected) BorderStrong else BorderSubtle,
                                        RoundedCornerShape(8.dp)
                                    )
                            ) {
                                Text(
                                    text = if (proto.isUltrasound) "⚡ Ultrasound (Silent)" else "🔊 Fast (Audible)",
                                    fontSize = 12.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Volume: $volumePercent%",
                        color = TextSecondary,
                        fontSize = 13.sp
                    )
                    Slider(
                        value = volumePercent.toFloat(),
                        onValueChange = { onVolumeChanged(it.toInt()) },
                        valueRange = 10f..100f,
                        colors = SliderDefaults.colors(
                            thumbColor = AccentSilver,
                            activeTrackColor = Color(0xFF505050),
                            inactiveTrackColor = Color(0xFF202020)
                        )
                    )
                }
            }
        }

        // --- 2. Messenger (Send Text) ---
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
                        text = "💬 Air-Gap Messenger (Send Text)",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = messageText,
                            onValueChange = { messageText = it },
                            placeholder = { Text("Enter message for PC...", color = TextTertiary) },
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = InputBg,
                                unfocusedContainerColor = InputBg,
                                focusedBorderColor = BorderStrong,
                                unfocusedBorderColor = BorderSubtle,
                                focusedTextColor = TextPrimary,
                                unfocusedTextColor = TextPrimary
                            ),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.weight(1f)
                        )

                        Button(
                            onClick = {
                                if (messageText.isNotBlank() && !isTransmitting) {
                                    val textToSend = messageText
                                    messageText = ""
                                    isTransmitting = true
                                    val timeStr = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
                                    sentMessages.add(Pair(timeStr, textToSend))

                                    scope.launch {
                                        val samples = dspEngine.encode(textToSend, selectedProtocol, volumePercent)
                                        playbackManager.playSamples(samples) {
                                            isTransmitting = false
                                        }
                                    }
                                }
                            },
                            enabled = !isTransmitting && messageText.isNotBlank(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFF282828),
                                contentColor = TextPrimary
                            ),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.height(52.dp)
                        ) {
                            Icon(Icons.Default.Send, contentDescription = "Send", tint = TextPrimary)
                        }
                    }

                    if (sentMessages.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Sent History:", color = TextSecondary, fontSize = 12.sp)
                        Spacer(modifier = Modifier.height(6.dp))
                        sentMessages.takeLast(4).forEach { (time, msg) ->
                            Text(
                                text = "[$time] Sent: $msg",
                                color = Color(0xFFD4D4D4),
                                fontSize = 13.sp,
                                modifier = Modifier.padding(vertical = 2.dp)
                            )
                        }
                    }
                }
            }
        }

        // --- 3. File Transfer (Send File) ---
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
                        text = "📁 File Transfer (Send File)",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val fileInfoStr = if (selectedFileName != null) {
                        "File: $selectedFileName (${selectedFileSize ?: 0} bytes)"
                    } else {
                        "No file selected."
                    }
                    Text(text = fileInfoStr, color = TextSecondary, fontSize = 13.sp)

                    Spacer(modifier = Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(
                            onClick = { filePickerLauncher.launch("*/*") },
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary),
                            shape = RoundedCornerShape(8.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, BorderStrong),
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.AttachFile, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Select File", fontSize = 13.sp)
                        }

                        Button(
                            onClick = {
                                val uri = selectedFileUri ?: return@Button
                                if (isTransmitting) return@Button

                                isTransmitting = true
                                fileSendProgress = 0f
                                fileLogText = "Reading and compressing file..."

                                scope.launch {
                                    try {
                                        val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                                            ?: throw Exception("Could not read file data")

                                        val chunked = FileChunker.chunkData(
                                            data = bytes,
                                            filename = selectedFileName ?: "document.bin",
                                            chunkSize = 48,
                                            compress = true
                                        )

                                        val totalPackets = chunked.packets.size
                                        for ((idx, packet) in chunked.packets.withIndex()) {
                                            val wrappedB85 = Base85.encodeWrapped(packet.serialize())
                                            fileLogText = "Transmitting packet ${idx + 1}/$totalPackets (${packet.type.name})"
                                            fileSendProgress = (idx + 1).toFloat() / totalPackets

                                            val samples = dspEngine.encode(wrappedB85, selectedProtocol, volumePercent)
                                            playbackManager.playSamples(samples)
                                        }

                                        fileLogText = "✔ File '$selectedFileName' transmitted successfully!"
                                    } catch (e: Exception) {
                                        fileLogText = "Transmission failed: ${e.message}"
                                    } finally {
                                        isTransmitting = false
                                    }
                                }
                            },
                            enabled = selectedFileUri != null && !isTransmitting,
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFF282828),
                                contentColor = TextPrimary
                            ),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text(if (isTransmitting) "Sending..." else "🚀 Transmit File", fontSize = 13.sp)
                        }
                    }

                    if (isTransmitting || fileSendProgress > 0f) {
                        Spacer(modifier = Modifier.height(12.dp))
                        LinearProgressIndicator(
                            progress = { fileSendProgress },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(8.dp),
                            color = AccentSilver,
                            trackColor = Color(0xFF202020)
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(text = fileLogText, color = TextSecondary, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}
