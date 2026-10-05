package com.acoustigap.app.protocol

import java.io.ByteArrayOutputStream

/**
 * Reassembles incoming chunks from acoustic air-gap, validates CRC32 and SHA-256.
 */
class TransferSessionReceiver {
    var metadata: FileMetadata? = null
        private set

    val receivedChunks = mutableMapOf<Int, ByteArray>()
    var isComplete: Boolean = false
        private set

    var assembledData: ByteArray? = null
        private set

    var error: String? = null
        private set

    fun reset() {
        metadata = null
        receivedChunks.clear()
        isComplete = false
        assembledData = null
        error = null
    }

    /**
     * Feed incoming raw decoded string (which may be a Base85 wrapped packet).
     * Returns true if a valid packet was consumed.
     */
    fun feedRawString(raw: String): Boolean {
        val bytes = Base85.decodeWrapped(raw) ?: return false
        val packet = Packet.deserialize(bytes) ?: return false
        return feedPacket(packet)
    }

    /**
     * Process a deserialized packet.
     */
    fun feedPacket(packet: Packet): Boolean {
        when (packet.type) {
            PacketType.START_SESSION -> {
                val meta = FileMetadata.deserialize(packet.payload)
                if (meta != null) {
                    metadata = meta
                    receivedChunks.clear()
                    isComplete = false
                    assembledData = null
                    error = null
                    return true
                }
            }
            PacketType.DATA_CHUNK -> {
                val meta = metadata ?: return false
                if (packet.chunkIndex < meta.totalChunks) {
                    receivedChunks[packet.chunkIndex] = packet.payload
                    checkCompletion()
                    return true
                }
            }
            PacketType.END_SESSION -> {
                checkCompletion()
                return true
            }
            else -> {}
        }
        return false
    }

    val progressPercent: Int
        get() {
            val total = metadata?.totalChunks ?: return 0
            if (total == 0) return 100
            return ((receivedChunks.size.toDouble() / total) * 100).toInt().coerceIn(0, 100)
        }

    private fun checkCompletion() {
        val meta = metadata ?: return
        if (receivedChunks.size >= meta.totalChunks) {
            // All chunks received in memory, assemble in index order
            val byteStream = ByteArrayOutputStream()
            for (i in 0 until meta.totalChunks) {
                val chunk = receivedChunks[i]
                if (chunk == null) {
                    return // Still missing chunk
                }
                byteStream.write(chunk)
            }

            val assembled = byteStream.toByteArray()
            val finalData = if (meta.compressed) {
                try {
                    FileChunker.decompressZlib(assembled)
                } catch (e: Exception) {
                    error = "Zlib decompression failed: ${e.message}"
                    return
                }
            } else {
                assembled
            }

            // Verify final SHA-256
            val actualHash = FileChunker.computeSha256(finalData)
            if (actualHash.equals(meta.sha256, ignoreCase = true)) {
                this.assembledData = finalData
                this.isComplete = true
                this.error = null
            } else {
                this.error = "SHA-256 mismatch! Expected: ${meta.sha256}, Actual: $actualHash"
            }
        }
    }
}
