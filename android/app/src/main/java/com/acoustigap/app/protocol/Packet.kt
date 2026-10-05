package com.acoustigap.app.protocol

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.zip.CRC32

/**
 * AcoustiGap Air-Gap Frame Packet
 *
 * Wire specification (15-byte fixed header):
 * - Magic: 2 bytes [0xAC, 0x61]
 * - Version: 1 byte (0x01)
 * - Type: 1 byte (START_SESSION=1, DATA_CHUNK=2, END_SESSION=3, ACK=4, NACK=5, PING=6, PONG=7)
 * - Session ID: 2 bytes Big-Endian (uint16)
 * - Chunk Index: 2 bytes Big-Endian (uint16)
 * - Total Chunks: 2 bytes Big-Endian (uint16)
 * - Payload Length: 1 byte (uint8, 0..255)
 * [Total header pre-CRC: 11 bytes]
 * - CRC-32: 4 bytes Big-Endian (uint32) calculated over (headerPreCrc + payload)
 * [Total Header: 15 bytes]
 * - Payload: NB
 */
enum class PacketType(val code: Byte) {
    START_SESSION(0x01),
    DATA_CHUNK(0x02),
    END_SESSION(0x03),
    ACK(0x04),
    NACK(0x05),
    PING(0x06),
    PONG(0x07);

    companion object {
        fun fromCode(code: Byte): PacketType? = entries.find { it.code == code }
    }
}

data class Packet(
    val type: PacketType,
    val sessionId: Int,
    val chunkIndex: Int,
    val totalChunks: Int,
    val payload: ByteArray,
    var crc32: Long = 0L
) {
    companion object {
        val MAGIC = byteArrayOf(0xAC.toByte(), 0x61.toByte())
        const val VERSION: Byte = 0x01
        const val HEADER_PRE_CRC_SIZE = 11
        const val HEADER_SIZE = 15

        fun calculateCrc32(headerPreCrc: ByteArray, payload: ByteArray): Long {
            val crc = CRC32()
            crc.update(headerPreCrc)
            crc.update(payload)
            return crc.value and 0xFFFFFFFFL
        }

        fun deserialize(data: ByteArray): Packet? {
            if (data.size < HEADER_SIZE) return null

            // Validate Magic Header
            if (data[0] != MAGIC[0] || data[1] != MAGIC[1]) return null

            val buffer = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN)
            buffer.position(2)

            val version = buffer.get()
            if (version != VERSION) return null

            val typeCode = buffer.get()
            val type = PacketType.fromCode(typeCode) ?: return null

            val sessionId = buffer.short.toInt() and 0xFFFF
            val chunkIndex = buffer.short.toInt() and 0xFFFF
            val totalChunks = buffer.short.toInt() and 0xFFFF
            val payloadLength = buffer.get().toInt() and 0xFF
            val packetCrc = buffer.int.toLong() and 0xFFFFFFFFL

            if (data.size < HEADER_SIZE + payloadLength) return null

            val payload = ByteArray(payloadLength)
            buffer.get(payload)

            // Reconstruct headerPreCrc for CRC verification
            val headerPreCrc = ByteArray(HEADER_PRE_CRC_SIZE)
            System.arraycopy(data, 0, headerPreCrc, 0, HEADER_PRE_CRC_SIZE)

            val expectedCrc = calculateCrc32(headerPreCrc, payload)
            if (packetCrc != expectedCrc) {
                return null // CRC checksum failure
            }

            return Packet(type, sessionId, chunkIndex, totalChunks, payload, packetCrc)
        }
    }

    fun serialize(): ByteArray {
        val payloadLen = payload.size
        require(payloadLen <= 255) { "Payload size $payloadLen exceeds max 255 bytes" }

        // 1. Pack header pre-CRC (11 bytes)
        val preBuf = ByteBuffer.allocate(HEADER_PRE_CRC_SIZE).order(ByteOrder.BIG_ENDIAN)
        preBuf.put(MAGIC)
        preBuf.put(VERSION)
        preBuf.put(type.code)
        preBuf.putShort(sessionId.toShort())
        preBuf.putShort(chunkIndex.toShort())
        preBuf.putShort(totalChunks.toShort())
        preBuf.put(payloadLen.toByte())
        val headerPreCrc = preBuf.array()

        // 2. Compute CRC32 over header_pre_crc + payload
        val computedCrc = calculateCrc32(headerPreCrc, payload)
        this.crc32 = computedCrc

        // 3. Assemble full 15-byte header + payload
        val fullBuf = ByteBuffer.allocate(HEADER_SIZE + payloadLen).order(ByteOrder.BIG_ENDIAN)
        fullBuf.put(headerPreCrc)
        fullBuf.putInt(computedCrc.toInt())
        fullBuf.put(payload)

        return fullBuf.array()
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as Packet
        return type == other.type &&
                sessionId == other.sessionId &&
                chunkIndex == other.chunkIndex &&
                totalChunks == other.totalChunks &&
                payload.contentEquals(other.payload)
    }

    override fun hashCode(): Int {
        var result = type.hashCode()
        result = 31 * result + sessionId
        result = 31 * result + chunkIndex
        result = 31 * result + totalChunks
        result = 31 * result + payload.contentHashCode()
        return result
    }
}
