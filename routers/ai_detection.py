from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect
from ultralytics import YOLO
import cv2
import numpy as np
import base64
import json
import os
from typing import List

router = APIRouter(
    prefix="/ai",
    tags=["ai_detection"],
)

# Load Model
MODEL_PATH = "access/best.pt"
# Check if model exists
if not os.path.exists(MODEL_PATH):
    print(f"WARNING: Model not found at {MODEL_PATH}. AI endpoints will fail.")
    model = None
else:
    model = YOLO(MODEL_PATH)

@router.post("/detect")
async def detect_image(file: UploadFile = File(...)):
    """
    Detect drowsiness from an uploaded image file.
    Returns JSON with detected classes and bounding boxes.
    """
    if model is None:
        return {"error": "Model not loaded"}
    
    # Read image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return {"error": "Invalid image"}

    # Inference
    results = model(img)
    
    # Process results
    detections = []
    for r in results:
        for box in r.boxes:
            # box.xyxy[0] is tensor, convert to list
            coords = box.xyxy[0].tolist() 
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            
            detections.append({
                "label": label,
                "confidence": round(conf, 2),
                "box": [int(x) for x in coords] # [x1, y1, x2, y2]
            })
            
    return {"detections": detections}

@router.websocket("/ws/detect")
async def websocket_detect(websocket: WebSocket):
    """
    WebSocket endpoint for real-time detection.
    Client sends: Bytes (Image)
    Server responds: JSON (Detections)
    """
    await websocket.accept()
    try:
        while True:
            # Receive image bytes
            data = await websocket.receive_bytes()
            
            if model is None:
                await websocket.send_json({"error": "Model not loaded"})
                continue

            # Convert bytes to numpy array
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                await websocket.send_json({"error": "Invalid frame"})
                continue
            
            # Inference (stream=True for speed)
            results = model(img, verbose=False) # verbose=False to reduce logs
            
            detections = []
            status = "awake" # Default status
            
            # Logic to determine driver status based on detection priority
            # Priority: Drowsy > Head Drop > Yawn > Phone > Distracted > Awake
            has_drowsy = False
            has_head_drop = False
            
            for r in results:
                for box in r.boxes:
                    coords = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    label = model.names[cls_id]
                    
                    if label == "drowsy": has_drowsy = True
                    if label == "head drop": has_head_drop = True
                    
                    detections.append({
                        "label": label,
                        "confidence": round(conf, 2),
                        "box": [int(x) for x in coords]
                    })
            
            # Priority: Drowsy > Head Drop > Yawn > Phone > Distracted > Awake
            detected_label = "awake" # Default

            # Sort detections by priority or just check flags.
            # We want the specific label name as status.
            
            # Check for high priority
            for d in detections:
                 lbl = d['label']
                 if lbl in ["drowsy", "head drop"]:
                     detected_label = lbl
                     break # Stop if found critical
            
            # If no critical, check secondary
            if detected_label == "awake":
                 for d in detections:
                      lbl = d['label']
                      if lbl in ["yawn", "phone", "distracted"]:
                          detected_label = lbl
                          break
            
            status = detected_label
            
            # Send result back
            await websocket.send_json({
                "status": status,
                "detections": detections
            })
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        try:
            await websocket.close()
        except:
            pass
