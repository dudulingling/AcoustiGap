package com.acoustigap.app.ui.screens

import android.content.Context
import android.os.Environment
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.acoustigap.app.protocol.Base85
import com.acoustigap.app.protocol.Packet
import com.acoustigap.app.protocol.TransferSessionReceiver
import com.acoustigap.app.ui.theme.*
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun ReceiverScreen(
    transferReceiver: TransferSessionReceiver,
    incomingRawTextFlow: kotlinx.coroutines.flow.SharedFlow<String>
) {
    val context = LocalContext.current

    val receivedMessages = remember { mutableStateListOf<Pair<String, String>>() }
    val completedFiles = remember { mutableStateListOf<Triple<String, Long, String>>() }

    var fileProgress by remember { mutableStateOf(0f) }
    var currentFileStatus by remember { mutableStateOf("Awaiting incoming transmission...") }
    var activeFilename by remember { mutableStateOf<String?>(null) }

    // Listen to incoming decoded text strings
    LaunchedEffect(incomingRawTextFlow) {
        incomingRawTextFlow.collect { rawText ->
            val timestamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())

            // Check if this text is an AcoustiGap wrapped binary packet
            if (rawText.startsWith("!B85:")) {
                val bytes = Base85.decodeWrapped(rawText)
                if (bytes != null) {
                    val pkt = Packet.deserialize(bytes)
                    if (pkt != null) {
                        transferReceiver.feedPacket(pkt)
                        val meta = transferReceiver.metadata
                        if (meta != null) {
                            activeFilename = meta.filename
                            val curr = transferReceiver.receivedChunks.size
                            val total = meta.totalChunks
                            fileProgress = (curr.toFloat() / maxOf(1, total)).coerceIn(0f, 1f)
                            currentFileStatus = "Receiving ${meta.filename} (Packet $curr/$total)"
                        }

                        if (transferReceiver.isComplete) {
                            val data = transferReceiver.assembledData
                            val meta = transferReceiver.metadata
                            if (data != null && meta != null) {
                                // Save file to device storage
                                try {
                                    val dir = File(context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "AcoustiGap")
                                    dir.mkdirs()
                                    val file = File(dir, meta.filename)
                                    FileOutputStream(file).use { it.write(data) }

                                    completedFiles.add(Triple(meta.filename, meta.fileSize, meta.sha256.take(8)))
                                    currentFileStatus = "✔ Verified & Saved: ${meta.filename} (${meta.fileSize} B)"
                                    Toast.makeText(context, "Received: ${meta.filename}", Toast.LENGTH_SHORT).show()
                                } catch (e: Exception) {
                                    currentFileStatus = "Save failed: ${e.message}"
                                }
                            }
                        }
                        return@collect
                    }
                }
            }

            // Otherwise, it's a plain messenger chat message
            receivedMessages.add(Pair(timestamp, rawText))
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BlackBg)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- 1. Status Indicator Header ---
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = CardDark),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BorderSubtle, RoundedCornerShape(10.dp))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "Acoustic Receiver",
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary,
                            fontSize = 15.sp
                        )
                        Text(
                            text = "48 kHz PCM • Listening on mic array",
                            color = TextSecondary,
                            fontSize = 12.sp
                        )
                    }

                    Surface(
                        color = Color(0xFF064E3B),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            text = "● ACTIVE LISTENING",
                            color = SuccessGreen,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                        )
                    }
                }
            }
        }

        // --- 2. Messenger (Received Messages) ---
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
                        text = "💬 Air-Gap Messenger (Received Messages)",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    if (receivedMessages.isEmpty()) {
                        Text(
                            text = "No messages received yet. Transmit from PC to see live messages here.",
                            color = TextTertiary,
                            fontSize = 13.sp,
                            modifier = Modifier.padding(vertical = 12.dp)
                        )
                    } else {
                        receivedMessages.takeLast(10).forEach { (time, msg) ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Text("[$time]", color = TextSecondary, fontSize = 12.sp)
                                Text("Received:", color = SuccessGreen, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                Text(msg, color = TextPrimary, fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }

        // --- 3. File Transfer Progress & Completed Files ---
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
                        text = "📁 Incoming File Transfer",
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 15.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    LinearProgressIndicator(
                        progress = { fileProgress },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp),
                        color = SuccessGreen,
                        trackColor = Color(0xFF202020)
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(text = currentFileStatus, color = TextSecondary, fontSize = 12.sp)

                    if (completedFiles.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(14.dp))
                        Text(
                            text = "Received & Verified Files:",
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary,
                            fontSize = 13.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        completedFiles.forEach { (name, size, hash) ->
                            Surface(
                                color = InputBg,
                                shape = RoundedCornerShape(6.dp),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 3.dp)
                                    .border(1.dp, BorderSubtle, RoundedCornerShape(6.dp))
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(8.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(name, color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                        Text("$size bytes • SHA-256: $hash...", color = TextSecondary, fontSize = 11.sp)
                                    }
                                    Surface(
                                        color = Color(0xFF064E3B),
                                        shape = RoundedCornerShape(6.dp)
                                    ) {
                                        Text(
                                            "VERIFIED",
                                            color = SuccessGreen,
                                            fontSize = 10.sp,
                                            fontWeight = FontWeight.Bold,
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
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
