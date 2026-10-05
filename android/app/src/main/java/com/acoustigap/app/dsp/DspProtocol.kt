package com.acoustigap.app.dsp

/**
 * AcoustiGap Acoustic Transmission Protocols
 * Interoperable with desktop DspEngine.
 */
enum class DspProtocol(
    val id: Int,
    val displayName: String,
    val isUltrasound: Boolean,
    val baseFreq: Double,
    val freqStep: Double,
    val description: String
) {
    NORMAL(
        id = 0,
        displayName = "Normal (Audible)",
        isUltrasound = false,
        baseFreq = 1875.0,
        freqStep = 187.5,
        description = "Standard audible acoustic transmission (1.8 kHz - 3.2 kHz)."
    ),
    FAST(
        id = 1,
        displayName = "Fast (Audible)",
        isUltrasound = false,
        baseFreq = 2000.0,
        freqStep = 250.0,
        description = "High-speed audible transmission (2.0 kHz - 4.5 kHz)."
    ),
    ULTRASOUND_FAST(
        id = 4,
        displayName = "Ultrasound Fast (Silent)",
        isUltrasound = true,
        baseFreq = 15500.0,
        freqStep = 250.0,
        description = "Near-ultrasound stealth channel (15.5 kHz - 19.5 kHz). Completely inaudible."
    );

    companion object {
        fun fromId(id: Int): DspProtocol = entries.find { it.id == id } ?: FAST
    }
}
