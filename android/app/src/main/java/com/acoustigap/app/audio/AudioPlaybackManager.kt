package com.acoustigap.app.audio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Manages low-latency audio playback for acoustic modulation.
 * Tuned for Samsung S24 Ultra stereo AKG speakers.
 */
class AudioPlaybackManager(
    private val sampleRate: Int = 48000
) {
    private var audioTrack: AudioTrack? = null

    suspend fun playSamples(samples: ShortArray, onComplete: () -> Unit = {}) = withContext(Dispatchers.IO) {
        val bufferSize = AudioTrack.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        ).coerceAtLeast(samples.size * 2)

        val track = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(sampleRate)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setBufferSizeInBytes(bufferSize)
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()

        audioTrack = track
        track.play()

        var written = 0
        while (written < samples.size) {
            val count = track.write(samples, written, samples.size - written)
            if (count <= 0) break
            written += count
        }

        // Wait for buffer to finish playing
        val playDurationMs = (samples.size.toDouble() / sampleRate * 1000.0).toLong() + 100
        kotlinx.coroutines.delay(playDurationMs)

        track.stop()
        track.release()
        audioTrack = null
        onComplete()
    }

    fun stop() {
        try {
            audioTrack?.pause()
            audioTrack?.flush()
            audioTrack?.stop()
            audioTrack?.release()
        } catch (_: Exception) {}
        audioTrack = null
    }
}
