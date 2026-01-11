
## AI Drowsiness Detection API

This module provides real-time driver drowsiness detection using a YOLOv8 model hosted on the backend.

### 1. WebSocket Endpoint (Real-time Streaming) - **Recommended** 🏆

This method is highly recommended for real-time applications as it maintains a persistent connection, reducing latency significantly compared to HTTP requests.

*   **URL:** `ws://<BACKEND_IP>:8000/ai/ws/detect`
*   **Method:** WebSocket
*   **Data Flow:**
    1.  **Client (Flutter App):**
        *   Establish a WebSocket connection.
        *   Capture camera frames continuously.
        *   Convert each frame to **Binary Bytes** (JPEG/PNG format).
        *   Send the binary data to the WebSocket server.
    2.  **Server (Backend):**
        *   Receives the image bytes.
        *   Processes the image using the YOLOv8 model.
        *   Returns a JSON response with detection results immediately.

*   **Server Response Format (JSON):**
    ```json
    {
      "status": "drowsy",  // Overall Status: "awake", "drowsy", "head drop", "yawn", "phone", "distracted"
      "detections": [
        {
          "label": "drowsy",
          "confidence": 0.88,
          "box": [100, 200, 300, 400] // [x1, y1, x2, y2] - Bounding Box Coordinates
        },
        {
           "label": "yawn",
           "confidence": 0.75,
           "box": [150, 250, 280, 350]
        }
      ]
    }
    ```

*   **Status Logic:**
    The `status` field provided in the response is prioritized as follows for easy UI logic:
    1.  **CRITICAL**: `"drowsy"`, `"head drop"` (Trigger RED Alert 🚨)
    2.  **WARNING**: `"yawn"`, `"phone"`, `"distracted"` (Trigger YELLOW Warning ⚠️)
    3.  **NORMAL**: `"awake"` (Green State ✅)

### 2. HTTP Endpoint (One-shot Detection) - *Backup*
Use this if WebSocket is not feasible or for testing single images.

*   **URL:** `http://<BACKEND_IP>:8000/ai/detect`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`
*   **Body:**
    *   `file`: The image file (binary).
*   **Response:** Same JSON structure as WebSocket (inside a `detections` key).
