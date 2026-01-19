# Sơ đồ Khối Hệ thống (Flowchart Tổng thể)

Dưới đây là sơ đồ luồng dữ liệu và hoạt động của hệ thống phát hiện buồn ngủ, từ lúc camera thu hình ảnh đến khi cảnh báo được phát ra. Bạn có thể sử dụng sơ đồ Mermaid này hoặc vẽ lại theo ý tưởng tương tự vào báo cáo.

```mermaid
graph TD
    %% Định nghĩa các node (khối)
    User((Người lái xe))
    Camera[Camera Điện thoại / Dashcam]
    MobileApp[Ứng dụng Mobile Android/Flutter]
    WebSocket{Kết nối WebSocket}
    
    subgraph "Backend Server (FastAPI)"
        Receiver[Bộ thu nhận dữ liệu]
        subgraph "Core AI Module"
            Preprocessor[Bộ tiền xử lý ảnh thích ứng\n(Adaptive Preprocessing)]
            YOLO[Mô hình AI YOLOv8\n(Object Detection)]
            Logic[Logic Phân tích & Ra quyết định]
        end
        ResponseGen[Tạo phản hồi JSON]
    end

    User -->|Hình ảnh khuôn mặt| Camera
    Camera -->|Frame Video (Raw)| MobileApp
    MobileApp -->|Gửi Frame (Binary)| WebSocket
    WebSocket -->|Frame| Receiver
    
    Receiver -->|Frame Gốc| Preprocessor
    Preprocessor -->|Frame Đã xử lý (Cân bằng sáng/nét)| YOLO
    
    YOLO -->|Kết quả (Bounding Boxes, Conf, Labels)| Logic
    Logic -->|Xác định trạng thái:\nAwake / Drowsy / Distracted| ResponseGen
    
    ResponseGen -->|JSON {Status, Detections}| WebSocket
    WebSocket -->|Dữ liệu phản hồi| MobileApp
    
    MobileApp -->|Hiển thị khung hình & Cảnh báo âm thanh| User

    %% Style cho đẹp
    style Backend Server fill:#f9f9f9,stroke:#333,stroke-width:2px
    style Core AI Module fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style MobileApp fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style YOLO fill:#ffccbc,stroke:#d84315,stroke-width:2px
```

## Giải thích chi tiết các khối chức năng:

1.  **Người lái xe (User)**: Đối tượng tương tác chính.
2.  **Thiết bị Di động (Mobile App)**:
    *   Thu thập dữ liệu hình ảnh từ Camera theo thời gian thực.
    *   Nén ảnh và gửi liên tục lên Server qua giao thức WebSocket (để giảm độ trễ).
    *   Nhận kết quả trả về và phát tín hiệu cảnh báo (loa, màn hình) nếu phát hiện nguy hiểm.
3.  **Kết nối WebSocket**: Kênh truyền thông hai chiều thời gian thực giữa App và Server, đảm bảo tốc độ phản hồi nhanh nhất (~50-100ms).
4.  **Backend Server**:
    *   **Bộ tiền xử lý (Preprocessor)**: Tự động điều chỉnh độ sáng, độ tương phản của ảnh (như đã mô tả ở phần thuật toán) để mô hình AI "nhìn" rõ hơn trong điều kiện thiếu sáng hoặc chói nắng.
    *   **Mô hình AI (YOLOv8)**: Nhận diện các đặc trưng: mắt nhắm (drowsy), ngáp (yawn), dùng điện thoại (phone), v.v.
    *   **Logic Phân tích**: Tổng hợp kết quả từ AI để đưa ra kết luận cuối cùng (Ví dụ: Có "drowsy" -> Báo động đỏ ngay).
