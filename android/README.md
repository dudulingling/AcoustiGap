# AcoustiGap Android Client (Kotlin)

Ứng dụng Android độc lập viết bằng **Kotlin + Jetpack Compose**, được thiết kế và tối ưu riêng cho **Samsung Galaxy S24 Ultra** (Snapdragon 8 Gen 3, One UI 6.1+ / Android 14/15) nhằm giao tiếp hai chiều hoàn hảo với phiên bản AcoustiGap Desktop trên Windows qua sóng âm (Acoustic Air-Gap).

---

## 🎯 Điểm Tối Ưu Đặc Biệt Cho Samsung Galaxy S24 Ultra

1. **Bypass Samsung Voice Focus & Beamforming (`AudioSource.UNPROCESSED`):**
   - Trên One UI, các API thu âm thông thường mặc định kích hoạt bộ lọc âm thanh vòm và chống ồn đàm thoại (Noise Suppression), vốn sẽ cắt gọt toàn bộ dải tần cận siêu âm (>10 kHz).
   - AcoustiGap Android sử dụng trực tiếp luồng `MediaRecorder.AudioSource.UNPROCESSED`, cho phép micro thu nhận nguyên vẹn toàn bộ dải tần từ **20 Hz đến 22,000+ Hz** ở tần số mẫu **48,000 Hz**.
2. **Khai thác hệ thống loa Stereo AKG Dynamic Range:**
   - Điều biến FSK trực tiếp qua `AudioTrack` ở chuẩn PCM 16-bit 48 kHz mono, phát tín hiệu cận siêu âm (`ULTRASOUND_FAST` 15.5 kHz – 19.5 kHz) hoàn toàn im lặng nhưng đạt công suất cao đến micro PC.
3. **Giao diện AMOLED Pure Dark (Tông Đen + Xám Khói + Bạc):**
   - Thiết kế đồng nhất hoàn toàn với giao diện Windows AcoustiGap, tối ưu năng lượng trên màn hình Dynamic AMOLED 2X của S24 Ultra.

---

## 📡 Tương Thích Giao Thức (Interoperability Với Windows)

- **Tần số lấy mẫu:** 48,000 Hz (đảm bảo dải Nyquist 24 kHz).
- **Cấu trúc gói tin 15-byte chuẩn:**
  ```text
  [Magic: 2B (0xAC, 0x61)] [Version: 1B (0x01)] [Type: 1B]
  [SessionID: 2B uint16] [ChunkIndex: 2B uint16] [TotalChunks: 2B uint16]
  [PayloadLen: 1B uint8] [CRC32: 4B uint32]
  [Payload: NB]
  ```
- **Kênh mã hóa Base85 (`!B85:...`):** Đồng bộ tuyệt đối với `base64.b85encode` / `b85decode` trên Windows Python.
- **Nén & Toàn vẹn:** Tích hợp `Deflater`/`Inflater` (zlib) và hàm băm `SHA-256` tự động kiểm tra tính toàn vẹn từng tập tin nhận được.

---

## 🛠 Hướng Dẫn Mở & Build Ứng Dụng

1. Mở **Android Studio** (Hedgehog, Iguana, Koala hoặc mới hơn).
2. Chọn **Open** -> Điều hướng đến thư mục `d:\Code\AcoustiGap\android`.
3. Chờ Gradle đồng bộ các thư viện Jetpack Compose và Kotlin 2.x.
4. Kết nối Samsung Galaxy S24 Ultra qua USB (bật USB Debugging trong Developer Options) hoặc chọn Emulator.
5. Bấm **Run ▶** để cài đặt trực tiếp lên điện thoại.

---

## 📁 Cấu Trúc Mã Nguồn

```
android/app/src/main/
├── AndroidManifest.xml          # Khai báo quyền RECORD_AUDIO, UNPROCESSED mic, FOREGROUND_SERVICE
├── res/                         # Tài nguyên biểu tượng ic_launcher (MDPI đến XXXHDPI), màu sắc, theme
└── java/com/acoustigap/app/
    ├── MainActivity.kt          # Điều hướng 4 tab (Sender, Receiver, Diagnostics, Settings)
    ├── protocol/
    │   ├── Packet.kt            # Cấu trúc frame 15-byte, CRC-32 IEEE 802.3
    │   ├── Base85.kt            # Bộ mã hóa/giải mã Base85 RFC 1924 tương thích Python
    │   ├── FileChunker.kt       # Cắt nhỏ file, nén zlib, tạo SHA-256 metadata
    │   └── TransferSession.kt   # Quản lý phiên truyền/nhận và lắp ghép file
    ├── dsp/
    │   ├── DspProtocol.kt       # Các dải tần số (FAST audible, ULTRASOUND_FAST silent)
    │   └── DspEngine.kt         # Điều biến sóng âm 48kHz, tính RMS dBFS, FFT energy
    ├── audio/
    │   ├── AudioCaptureManager.kt # Thu âm mic S24 Ultra (UNPROCESSED 48kHz)
    │   └── AudioPlaybackManager.kt# Phát sóng âm qua loa stereo AKG
    └── ui/
        ├── theme/Theme.kt       # AMOLED Pure Dark (Black + Charcoal Grey)
        ├── components/          # Canvas Spectrogram biểu diễn phổ tần số
        └── screens/
            ├── SenderScreen.kt       # Tab Sender (Gửi tin nhắn & Gửi file)
            ├── ReceiverScreen.kt     # Tab Receiver (Nhận tin nhắn & Nhận file)
            ├── DiagnosticsScreen.kt  # Tab Diagnostics (Đo tiếng ồn & SNR)
            └── SettingsScreen.kt     # Cấu hình phần cứng S24 Ultra & Protocol
```
