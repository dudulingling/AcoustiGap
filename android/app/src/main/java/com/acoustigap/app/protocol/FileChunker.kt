package com.acoustigap.app.protocol

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.util.zip.Deflater
import java.util.zip.Inflater

/**
 * File Metadata serialized into START_SESSION packet payload.
 * Binary format: [raw_sha256: 32B][file_size: 4B][total_chunks: 2B][compressed: 1B][name_len: 1B][filename: NB]
 */
data class FileMetadata(
    val filename: String,
    val fileSize: Long,
    val totalChunks: Int,
    val sha256: String,
    val compressed: Boolean
) {
    companion object {
        const val HEADER_BYTES = 40

        fun hexStringToByteArray(s: String): ByteArray {
            val len = s.length
            val data = ByteArray(len / 2)
            var i = 0
            while (i < len) {
                data[i / 2] = ((Character.digit(s[i], 16) shl 4) + Character.digit(s[i + 1], 16)).toByte()
                i += 2
            }
            return data
        }

        fun byteArrayToHexString(bytes: ByteArray): String {
            val sb = StringBuilder()
            for (b in bytes) {
                sb.append(String.format("%02x", b.toInt() and 0xFF))
            }
            return sb.toString()
        }

        fun deserialize(data: ByteArray): FileMetadata? {
            if (data.size < HEADER_BYTES) return null
            val buffer = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN)

            val rawHash = ByteArray(32)
            buffer.get(rawHash)

            val fileSize = buffer.int.toLong() and 0xFFFFFFFFL
            val totalChunks = buffer.short.toInt() and 0xFFFF
            val compressed = buffer.get().toInt() != 0
            val nameLen = buffer.get().toInt() and 0xFF

            if (data.size < HEADER_BYTES + nameLen) return null

            val nameBytes = ByteArray(nameLen)
            buffer.get(nameBytes)
            val filename = String(nameBytes, Charsets.UTF_8)

            return FileMetadata(
                filename = filename,
                fileSize = fileSize,
                totalChunks = totalChunks,
                sha256 = byteArrayToHexString(rawHash),
                compressed = compressed
            )
        }
    }

    fun serialize(): ByteArray {
        val rawHash = hexStringToByteArray(sha256)
        val nameBytes = filename.toByteArray(Charsets.UTF_8).take(32).toByteArray()

        val buffer = ByteBuffer.allocate(HEADER_BYTES + nameBytes.size).order(ByteOrder.BIG_ENDIAN)
        buffer.put(rawHash)
        buffer.putInt(fileSize.toInt())
        buffer.putShort(totalChunks.toShort())
        buffer.put(if (compressed) 1.toByte() else 0.toByte())
        buffer.put(nameBytes.size.toByte())
        buffer.put(nameBytes)

        return buffer.array()
    }
}

data class ChunkedFile(
    val metadata: FileMetadata,
    val packets: List<Packet>
)

object FileChunker {
    const val DEFAULT_CHUNK_SIZE = 48

    fun computeSha256(data: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(data)
        return FileMetadata.byteArrayToHexString(hash)
    }

    fun compressZlib(data: ByteArray): ByteArray {
        val deflater = Deflater(Deflater.BEST_COMPRESSION)
        deflater.setInput(data)
        deflater.finish()

        val outputStream = ByteArrayOutputStream(data.size)
        val buffer = ByteArray(1024)
        while (!deflater.finished()) {
            val count = deflater.deflate(buffer)
            outputStream.write(buffer, 0, count)
        }
        deflater.end()
        return outputStream.toByteArray()
    }

    fun decompressZlib(compressedData: ByteArray): ByteArray {
        val inflater = Inflater()
        inflater.setInput(compressedData)

        val outputStream = ByteArrayOutputStream(compressedData.size * 2)
        val buffer = ByteArray(1024)
        while (!inflater.finished()) {
            val count = inflater.inflate(buffer)
            outputStream.write(buffer, 0, count)
        }
        inflater.end()
        return outputStream.toByteArray()
    }

    fun chunkData(
        data: ByteArray,
        filename: String = "payload.bin",
        sessionId: Int = 1,
        chunkSize: Int = DEFAULT_CHUNK_SIZE,
        compress: Boolean = true
    ): ChunkedFile {
        val rawSize = data.size.toLong()
        val sha256 = computeSha256(data)

        var isCompressed = false
        var dataToSend = data

        if (compress && data.size > 32) {
            val compressed = compressZlib(data)
            if (compressed.size < data.size) {
                dataToSend = compressed
                isCompressed = true
            }
        }

        // Slice into chunks
        val rawChunks = mutableListOf<ByteArray>()
        var offset = 0
        while (offset < dataToSend.size) {
            val len = minOf(chunkSize, dataToSend.size - offset)
            val chunk = ByteArray(len)
            System.arraycopy(dataToSend, offset, chunk, 0, len)
            rawChunks.add(chunk)
            offset += len
        }

        if (rawChunks.isEmpty()) {
            rawChunks.add(ByteArray(0))
        }

        val totalChunks = rawChunks.size
        val metadata = FileMetadata(
            filename = filename,
            fileSize = rawSize,
            totalChunks = totalChunks,
            sha256 = sha256,
            compressed = isCompressed
        )

        val packets = mutableListOf<Packet>()

        // 1. START_SESSION packet
        packets.add(
            Packet(
                type = PacketType.START_SESSION,
                sessionId = sessionId,
                chunkIndex = 0,
                totalChunks = totalChunks,
                payload = metadata.serialize()
            )
        )

        // 2. DATA_CHUNK packets (0-indexed to totalChunks - 1)
        for (idx in rawChunks.indices) {
            packets.add(
                Packet(
                    type = PacketType.DATA_CHUNK,
                    sessionId = sessionId,
                    chunkIndex = idx,
                    totalChunks = totalChunks,
                    payload = rawChunks[idx]
                )
            )
        }

        // 3. END_SESSION packet
        val endPayload = sha256.take(16).toByteArray(Charsets.US_ASCII)
        packets.add(
            Packet(
                type = PacketType.END_SESSION,
                sessionId = sessionId,
                chunkIndex = totalChunks,
                totalChunks = totalChunks,
                payload = endPayload
            )
        )

        return ChunkedFile(metadata, packets)
    }
}
