# Các Thuật toán Sử dụng trong Hệ thống

Dưới đây là mô tả các thuật toán chính được sử dụng trong hệ thống phát hiện buồn ngủ, trình bày dưới dạng mã giả (Pseudocode) để đưa vào báo cáo.

## 1. Thuật toán Tiền xử lý Ảnh Thích ứng (Adaptive Image Preprocessing)

Thuật toán này giúp chuẩn hóa chất lượng ảnh đầu vào dựa trên điều kiện ánh sáng môi trường trước khi đưa vào mô hình AI, nhằm tăng độ chính xác.

**Input:** Frame ảnh gốc từ Camera ($I_{raw}$)
**Output:** Frame ảnh đã xử lý ($I_{processed}$)

```text
Algorithm AdaptivePreprocessing(I_raw):
    # Bước 1: Phân tích độ sáng
    I_small = Resize(I_raw, 64x64)          // Giảm kích thước để tính toán nhanh
    I_gray = ConvertToGray(I_small)
    Brightness = Mean(I_gray)               // Tính độ sáng trung bình (0-255)

    I_processed = I_raw

    # Bước 2: Điều chỉnh theo ngữ cảnh
    IF Brightness < 60 THEN                 // Môi trường Tối
        # Tăng sáng và cân bằng chi tiết
        I_processed = GammaCorrection(I_processed, gamma=2.0)
        I_processed = GaussianBlur(I_processed, kernel=(5,5))
        I_processed = CLAHE(I_processed, clipLimit=3.0)      // Cân bằng histogram thích ứng
    
    ELSE IF Brightness > 180 THEN           // Môi trường Chói sáng
        # Giảm sáng và khử lóa
        I_processed = GammaCorrection(I_processed, gamma=0.6)
        I_processed = GaussianBlur(I_processed, kernel=(5,5))
        I_processed = CLAHE(I_processed, clipLimit=1.5)
    
    ELSE                                    // Môi trường Bình thường
        # Chỉ làm nét nhẹ để nổi bật đặc trưng
        I_processed = Sharpen(I_processed)
    
    RETURN I_processed
```

---

## 2. Thuật toán Chính: Phát hiện và Cảnh báo (Main Detection & Warning Logic)

Đây là quy trình xử lý chính diễn ra trên Server (Real-time Pipeline).

**Input:** Luồng video từ Client (Stream)
**Output:** Trạng thái tài xế ($Status$) và Danh sách vật thể ($Detections$)

```text
Algorithm DrowsinessDetectionLoop:
    Model = LoadYOLOv8("best.pt")
    
    WHILE True DO:
        # Nhận dữ liệu
        Frame_raw = ReceiveFromWebSocket()
        IF Frame_raw is Empty THEN BREAK
        
        # Tiền xử lý
        Frame_input = AdaptivePreprocessing(Frame_raw)
        
        # Nhận diện (Inference)
        # Model trả về danh sách các BoundingBox, Class, Confidence
        Results = Model.Predict(Frame_input)
        
        Detections = List()
        Has_Critical_Sign = False
        Has_Warning_Sign = False
        
        FOR Box IN Results DO:
            Label = GetClassLabel(Box)
            Confidence = GetConfidence(Box)
            
            Add {Label, Confidence, Coordinates} INTO Detections
            
            # Phân loại mức độ nguy hiểm
            IF Label IN ["drowsy", "head drop"] THEN
                Has_Critical_Sign = True
            ELSE IF Label IN ["yawn", "phone", "distracted"] THEN
                Has_Warning_Sign = True
            END IF
        END FOR
        
        # Logic Quyết định Trạng thái (Priority Logic)
        IF Has_Critical_Sign IS True THEN
            Status = "drowsy"           // BÁO ĐỘNG ĐỎ
        ELSE IF Has_Warning_Sign IS True THEN
            Status = DeterminedLabel    // "yawn" / "phone" / ...
        ELSE
            Status = "awake"            // BÌNH THƯỜNG
        END IF
        
        # Trản hồi
        SendJSON(Status, Detections)
    END WHILE
```

---

## 3. Lý thuyết Nền tảng (Mô tả ngắn gọn)

Ngoài giả mã, bạn có thể nêu tên các kỹ thuật sau:

1.  **AI Model**: Sử dụng kiến trúc **YOLOv8** (You Only Look Once version 8) - mạng nơ-ron tích chập (CNN) tối ưu cho bài toán nhận diện vật thể thời gian thực (Real-time Object Detection).
2.  **Computer Vision**:
    *   **CLAHE**: Cân bằng histogram thích ứng hạn chế độ tương phản (Contrast Limited Adaptive Histogram Equalization) để xử lý ảnh thiếu sáng mà không làm nhiễu hạt quá mức.
    *   **Gamma Correction**: Phép biến đổi phi tuyến tính để thay đổi độ chói của ảnh ($V_{out} = V_{in}^{\gamma}$).
