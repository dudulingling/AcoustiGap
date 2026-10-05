package com.acoustigap.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CallReceived
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.acoustigap.app.audio.AudioCaptureManager
import com.acoustigap.app.audio.AudioPlaybackManager
import com.acoustigap.app.dsp.DspEngine
import com.acoustigap.app.dsp.DspProtocol
import com.acoustigap.app.protocol.TransferSessionReceiver
import com.acoustigap.app.ui.screens.DiagnosticsScreen
import com.acoustigap.app.ui.screens.ReceiverScreen
import com.acoustigap.app.ui.screens.SenderScreen
import com.acoustigap.app.ui.screens.SettingsScreen
import com.acoustigap.app.ui.theme.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val dspEngine = DspEngine(sampleRate = 48000)
    private val captureManager = AudioCaptureManager(sampleRate = 48000)
    private val playbackManager = AudioPlaybackManager(sampleRate = 48000)
    private val transferReceiver = TransferSessionReceiver()

    private val incomingTextFlow = MutableSharedFlow<String>(extraBufferCapacity = 32)
    private var lastCapturedChunk: ShortArray = ShortArray(0)

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val recordGranted = permissions[Manifest.permission.RECORD_AUDIO] ?: false
        if (recordGranted) {
            captureManager.startCapture()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request runtime permissions for Android 13/14+
        val requiredPerms = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requiredPerms.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val allGranted = requiredPerms.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }

        if (allGranted) {
            captureManager.startCapture()
        } else {
            requestPermissionLauncher.launch(requiredPerms.toTypedArray())
        }

        // Background listener on audio buffer stream
        lifecycleScope.launch {
            captureManager.audioBufferFlow.collect { chunk ->
                lastCapturedChunk = chunk
            }
        }

        setContent {
            AcoustiGapTheme {
                MainAppScreen()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        captureManager.stopCapture()
        playbackManager.stop()
    }

    @OptIn(ExperimentalMaterial3Api::class)
    @Composable
    fun MainAppScreen() {
        var selectedTabIndex by remember { mutableIntStateOf(0) }
        var selectedProtocol by remember { mutableStateOf(DspProtocol.FAST) }
        var volumePercent by remember { mutableIntStateOf(70) }

        var currentRmsDb by remember { mutableFloatStateOf(-75f) }
        val audioLevels = remember { mutableStateListOf<Float>() }

        LaunchedEffect(Unit) {
            captureManager.rmsLevelFlow.collect { db ->
                currentRmsDb = db
                val normalized = ((db + 80f) / 70f).coerceIn(0.02f, 1f)
                if (audioLevels.size >= 48) {
                    audioLevels.removeAt(0)
                }
                audioLevels.add(normalized)
            }
        }

        Scaffold(
            topBar = {
                Surface(
                    color = BlackBg,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "🔊 AcoustiGap",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 18.sp,
                                    color = TextPrimary
                                )
                                Text(
                                    text = "Samsung S24 Ultra • 48 kHz FSK Engine",
                                    fontSize = 11.sp,
                                    color = TextSecondary
                                )
                            }

                            // Active Status Badge
                            Surface(
                                color = Color(0xFF064E3B),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text(
                                    text = "● LISTENING",
                                    color = SuccessGreen,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                )
                            }
                        }
                    }
                }
            },
            bottomBar = {
                NavigationBar(
                    containerColor = CardDark,
                    tonalElevation = 0.dp,
                    modifier = Modifier.border(1.dp, BorderSubtle)
                ) {
                    val tabs = listOf(
                        Triple("Sender", Icons.Default.Send, 0),
                        Triple("Receiver", Icons.Default.CallReceived, 1),
                        Triple("Diagnostics", Icons.Default.Build, 2),
                        Triple("Settings", Icons.Default.Settings, 3)
                    )

                    tabs.forEach { (label, icon, index) ->
                        val isSelected = selectedTabIndex == index
                        NavigationBarItem(
                            icon = { Icon(icon, contentDescription = label) },
                            label = { Text(label, fontSize = 11.sp, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal) },
                            selected = isSelected,
                            onClick = { selectedTabIndex = index },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = TextPrimary,
                                selectedTextColor = TextPrimary,
                                unselectedIconColor = TextSecondary,
                                unselectedTextColor = TextSecondary,
                                indicatorColor = Color(0xFF282828)
                            )
                        )
                    }
                }
            }
        ) { paddingValues ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .background(BlackBg)
            ) {
                when (selectedTabIndex) {
                    0 -> SenderScreen(
                        dspEngine = dspEngine,
                        playbackManager = playbackManager,
                        selectedProtocol = selectedProtocol,
                        onProtocolChanged = { selectedProtocol = it },
                        volumePercent = volumePercent,
                        onVolumeChanged = { volumePercent = it }
                    )
                    1 -> ReceiverScreen(
                        transferReceiver = transferReceiver,
                        incomingRawTextFlow = incomingTextFlow
                    )
                    2 -> DiagnosticsScreen(
                        dspEngine = dspEngine,
                        audioLevels = audioLevels,
                        currentRmsDb = currentRmsDb,
                        captureBufferProvider = { lastCapturedChunk }
                    )
                    3 -> SettingsScreen()
                }
            }
        }
    }
}
