package com.acoustigap.app.protocol

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Standard RFC 1924 / Python Base85 implementation for binary acoustic framing.
 * Exactly compatible with Python's `base64.b85encode` / `b85decode`.
 */
object Base85 {
    private const val PREFIX = "!B85:"
    private const val B85_CHARS =
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~"

    private val DECODE_MAP = IntArray(256) { -1 }.apply {
        for (i in B85_CHARS.indices) {
            this[B85_CHARS[i].code] = i
        }
    }

    /**
     * Encodes a byte array to Base85 string matching Python's base64.b85encode.
     */
    fun encode(data: ByteArray): String {
        if (data.isEmpty()) return ""

        val sb = StringBuilder()
        val remainder = data.size % 4
        val paddedLen = if (remainder == 0) data.size else data.size + (4 - remainder)
        val buffer = ByteArray(paddedLen)
        System.arraycopy(data, 0, buffer, 0, data.size)

        for (i in 0 until paddedLen step 4) {
            val v = ((buffer[i].toLong() and 0xFF) shl 24) or
                    ((buffer[i + 1].toLong() and 0xFF) shl 16) or
                    ((buffer[i + 2].toLong() and 0xFF) shl 8) or
                    (buffer[i + 3].toLong() and 0xFF)

            var value = v
            val chars = CharArray(5)
            for (j in 4 downTo 0) {
                chars[j] = B85_CHARS[(value % 85).toInt()]
                value /= 85
            }
            sb.append(chars)
        }

        if (remainder != 0) {
            val trim = 4 - remainder
            sb.setLength(sb.length - trim)
        }

        return sb.toString()
    }

    /**
     * Decodes a Base85 string matching Python's base64.b85decode.
     */
    fun decode(encoded: String): ByteArray {
        if (encoded.isEmpty()) return ByteArray(0)

        val remainder = encoded.length % 5
        val paddedLen = if (remainder == 0) encoded.length else encoded.length + (5 - remainder)
        val sb = StringBuilder(encoded)
        // Pad with highest symbol '~'
        for (i in 0 until (5 - remainder) % 5) {
            sb.append('~')
        }

        val outBytes = mutableListOf<Byte>()
        for (i in 0 until paddedLen step 5) {
            var value = 0L
            for (j in 0 until 5) {
                val c = sb[i + j].code
                val digit = if (c < 256) DECODE_MAP[c] else -1
                if (digit == -1) throw IllegalArgumentException("Invalid Base85 character: ${sb[i + j]}")
                value = value * 85 + digit
            }

            outBytes.add(((value ushr 24) and 0xFF).toByte())
            outBytes.add(((value ushr 16) and 0xFF).toByte())
            outBytes.add(((value ushr 8) and 0xFF).toByte())
            outBytes.add((value and 0xFF).toByte())
        }

        val resultSize = if (remainder == 0) outBytes.size else outBytes.size - (5 - remainder)
        val result = ByteArray(resultSize)
        for (i in 0 until resultSize) {
            result[i] = outBytes[i]
        }
        return result
    }

    /**
     * Encodes binary packet into AcoustiGap wrapped format "!B85:..."
     */
    fun encodeWrapped(packetData: ByteArray): String {
        return PREFIX + encode(packetData)
    }

    /**
     * Checks if string has AcoustiGap binary packet wrapper and decodes it.
     */
    fun decodeWrapped(text: String): ByteArray? {
        if (!text.startsWith(PREFIX)) return null
        return try {
            decode(text.substring(PREFIX.length))
        } catch (e: Exception) {
            null
        }
    }
}
