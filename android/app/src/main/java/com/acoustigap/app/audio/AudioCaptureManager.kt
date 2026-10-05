package com.acoustigap.app.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.math.log10
import kotlin.math.sqrt

/**
 * Manages low-latency audio capture from device microphones.
 *
 * SPECIFIC OPTIMIZATIONS FOR SAMSUNG S24 ULTRA (One UI 6.1+ / Android 14+):
 * - AudioSource is set to UNPROCESSED (or VOICE_RECOGNITION fallback).
 * - This bypasses Samsung's 'Voice Focus' AGC and beamforming algorithms,
 *   which would otherwise attenuate or eliminate ultrasonic FSK signals (15-20 kHz).
 */
class AudioCaptureManager(
    val sampleRate: Int = 48000
) {
    private var audioRecord: AudioRecord? = null
    private var recordingJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO)

    private val _audioBufferFlow = MutableSharedFlow<ShortArray>(extraBufferCapacity = 64)
    val audioBufferFlow: SharedFlow<ShortArray> = _audioBufferFlow

    private val _rmsLevelFlow = MutableSharedFlow<Float>(extraBufferCapacity = 8)
    val rmsLevelFlow: SharedFlow<Float> = _rmsLevelFlow

    var isCapturing: Boolean = false
        private set

    @SuppressLint("MissingPermission")
    fun startCapture() {
        if (isCapturing) return

        val minBufferSize = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )
        val bufferSize = (minBufferSize * 2).coerceAtLeast(4096)

        // Select UNPROCESSED audio source on Samsung S24 Ultra to avoid One UI noise reduction filtering
        val audioSource = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            MediaRecorder.AudioSource.UNPROCESSED
        } else {
            MediaRecorder.AudioSource.VOICE_RECOGNITION
        }

        try {
            audioRecord = AudioRecord(
                audioSource,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            )
        } catch (_: Exception) {
            // Fallback to VOICE_RECOGNITION if UNPROCESSED is unsupported
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            )
        }

        audioRecord?.startRecording()
        isCapturing = true

        recordingJob = scope.launch {
            val chunk = ShortArray(2048)
            while (isActive && isCapturing) {
                val read = audioRecord?.read(chunk, 0, chunk.size) ?: -1
                if (read > 0) {
                    val frame = ShortArray(read)
                    System.arraycopy(chunk, 0, frame, 0, read)
                    _audioBufferFlow.emit(frame)

                    // Calculate RMS dB level
                    var sum = 0.0
                    for (i in 0 until read) {
                        val norm = frame[i].toDouble() / 32768.0
                        sum += norm * norm
                    }
                    val rms = sqrt(sum / read)
                    val db = if (rms > 1e-5) (20.0 * log10(rms)).toFloat() else -90f
                    _rmsLevelFlow.emit(db)
                }
            }
        }
    }

    fun stopCapture() {
        isCapturing = false
        recordingJob?.cancel()
        recordingJob = null
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (_: Exception) {}
        audioRecord = null
    }
}
