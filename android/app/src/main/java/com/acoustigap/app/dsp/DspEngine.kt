package com.acoustigap.app.dsp

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.log10
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * AcoustiGap Native Audio Digital Signal Processor
 * Operates at 48,000 Hz 16-bit PCM Mono.
 * Synthesizes smoothed FSK tones for transmission and performs real-time frequency analysis.
 */
class DspEngine(
    val sampleRate: Int = 48000
) {
    companion object {
        const val PREAMBLE_DURATION_MS = 40
        const val SYMBOL_DURATION_MS = 16
        const val NUM_TONES = 16 // 4-bit per symbol (Hexadecimal FSK)
    }

    /**
     * Synthesizes 16-bit PCM audio samples for the provided text string.
     */
    fun encode(text: String, protocol: DspProtocol = DspProtocol.FAST, volumePercent: Int = 70): ShortArray {
        return encodeBytes(text.toByteArray(Charsets.UTF_8), protocol, volumePercent)
    }

    /**
     * Modulates raw bytes into smoothed 48 kHz FSK waveform.
     */
    fun encodeBytes(data: ByteArray, protocol: DspProtocol = DspProtocol.FAST, volumePercent: Int = 70): ShortArray {
        val volume = (volumePercent.coerceIn(5, 100) / 100.0) * 0.9
        val symbolSamples = (sampleRate * (SYMBOL_DURATION_MS / 1000.0)).toInt()
        val preambleSamples = (sampleRate * (PREAMBLE_DURATION_MS / 1000.0)).toInt()

        // Preamble tones (Sync mark)
        val syncFreq1 = protocol.baseFreq - protocol.freqStep
        val syncFreq2 = protocol.baseFreq + (NUM_TONES * protocol.freqStep)

        // Convert each byte to 2 4-bit nibbles
        val symbols = mutableListOf<Int>()
        for (b in data) {
            val u = b.toInt() and 0xFF
            symbols.add((u shr 4) and 0x0F) // High nibble
            symbols.add(u and 0x0F)        // Low nibble
        }

        val totalSamples = (preambleSamples * 2) + (symbols.size * symbolSamples) + symbolSamples
        val output = ShortArray(totalSamples)
        var writeIdx = 0

        // 1. Generate Preamble Tone 1
        writeTone(output, writeIdx, preambleSamples, syncFreq1, volume)
        writeIdx += preambleSamples

        // 2. Generate Preamble Tone 2
        writeTone(output, writeIdx, preambleSamples, syncFreq2, volume)
        writeIdx += preambleSamples

        // 3. Modulate Data Symbols
        for (sym in symbols) {
            val freq = protocol.baseFreq + (sym * protocol.freqStep)
            writeTone(output, writeIdx, symbolSamples, freq, volume)
            writeIdx += symbolSamples
        }

        // 4. Trailer sync tone
        writeTone(output, writeIdx, symbolSamples, syncFreq1, volume)

        return output
    }

    /**
     * Writes a sine wave of specified frequency with Hann-window smoothing at the boundaries.
     */
    private fun writeTone(dest: ShortArray, offset: Int, count: Int, freq: Double, volume: Double) {
        val angularFreq = 2.0 * PI * freq / sampleRate
        for (i in 0 until count) {
            if (offset + i >= dest.size) break

            // Raised-cosine windowing at edges (first and last 10%)
            val ramp = when {
                i < count * 0.1 -> 0.5 * (1.0 - cos(PI * i / (count * 0.1)))
                i > count * 0.9 -> 0.5 * (1.0 - cos(PI * (count - i) / (count * 0.1)))
                else -> 1.0
            }

            val sampleVal = sin(i * angularFreq) * volume * ramp
            dest[offset + i] = (sampleVal * 32767.0).toInt().coerceIn(-32768, 32767).toShort()
        }
    }

    /**
     * Computes Goertzel energy at target frequency.
     */
    fun computeGoertzelEnergy(samples: ShortArray, targetFreq: Double, numSamples: Int): Double {
        val k = (0.5 + ((numSamples * targetFreq) / sampleRate)).toInt()
        val omega = (2.0 * PI * k) / numSamples
        val sine = sin(omega)
        val cosine = cos(omega)
        val coeff = 2.0 * cosine

        var q0 = 0.0
        var q1 = 0.0
        var q2 = 0.0

        for (i in 0 until minOf(numSamples, samples.size)) {
            val sample = samples[i] / 32768.0
            q0 = coeff * q1 - q2 + sample
            q2 = q1
            q1 = q0
        }

        return q1 * q1 + q2 * q2 - q1 * q2 * coeff
    }

    /**
     * Noise Profile and Diagnostic Assessment
     */
    data class NoiseProfile(
        val rmsDb: Double,
        val peakDb: Double,
        val health: String,
        val recommendation: String,
        val topFreqs: List<Pair<Double, Double>>
    )

    /**
     * Analyze ambient noise buffer for Channel Diagnostics.
     */
    fun analyzeNoise(samples: ShortArray): NoiseProfile {
        if (samples.isEmpty()) {
            return NoiseProfile(-90.0, -90.0, "QUIET", "Excellent quiet conditions.", emptyList())
        }

        var sumSq = 0.0
        var peak = 0.0
        for (s in samples) {
            val norm = s.toDouble() / 32768.0
            val abs = kotlin.math.abs(norm)
            if (abs > peak) peak = abs
            sumSq += norm * norm
        }

        val rms = sqrt(sumSq / samples.size)
        val rmsDb = if (rms > 1e-6) 20.0 * log10(rms) else -90.0
        val peakDb = if (peak > 1e-6) 20.0 * log10(peak) else -90.0

        val (health, rec) = when {
            rmsDb > -30.0 -> Pair("NOISY", "High ambient noise. Move phone closer to speaker.")
            rmsDb > -48.0 -> Pair("MODERATE", "Moderate room noise. Use FAST or ULTRASOUND_FAST protocol.")
            else -> Pair("EXCELLENT", "Pristine channel health. Optimal for high-speed acoustic transmission.")
        }

        // Sample key frequency bins
        val testFreqs = listOf(1500.0, 2500.0, 4000.0, 8000.0, 16000.0, 18000.0)
        val topFreqs = testFreqs.map { f ->
            val e = computeGoertzelEnergy(samples, f, minOf(512, samples.size))
            val db = if (e > 1e-9) 10.0 * log10(e) else -90.0
            Pair(f, db)
        }.sortedByDescending { it.second }

        return NoiseProfile(rmsDb, peakDb, health, rec, topFreqs)
    }
}
