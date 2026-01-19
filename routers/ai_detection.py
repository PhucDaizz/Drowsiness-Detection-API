from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect
from ultralytics import YOLO
import cv2
import numpy as np
import base64
import json
import os
from typing import List
from utils.image_preprocessor import ImagePreprocessor

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
    
# Initialize Preprocessor Globally (Stateless/Shared) or Per Request?
# Python objects are generally thread-safe for read-only or local vars. 
# Our preprocessor stores `current_mode` and caches, so it's stateful.
# For async, better to instantiate inside function or use a dependency.
# Simplest: Instantiate inside handler for isolation or use one global if careful.
# Given it caches LUT, global is better for perf, but `current_mode` is per-frame state.
# Let's instantiate per request to be safe with state `current_mode`.
# Or better: Global instance but return mode from process() and don't rely on self.current_mode strictly.
# Based on code provided: `self.current_mode` is modified. So one instance per connection/request is safest.

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

    # Preprocess
    preprocessor = ImagePreprocessor()
    processed_img, mode = preprocessor.process(img)

    # Inference
    results = model(processed_img)
    
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
async def websocket_detect(websocket: WebSocket, user_id: int = None):
    """
    WebSocket endpoint for real-time detection.
    Usage: ws://localhost:8000/ai/ws/detect?user_id=1
    """
    await websocket.accept()
    
    # Instantiate Preprocessor
    preprocessor = ImagePreprocessor()
    
    # Alert Throttling
    import time
    last_alert_time = 0
    ALERT_COOLDOWN = 15 # Seconds
    
    try:
        while True:
            # Receive image bytes
            data = await websocket.receive_bytes()
            
            if model is None:
                await websocket.send_json({"error": "Model not loaded"})
                continue

            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                await websocket.send_json({"error": "Invalid frame"})
                continue
            
            processed_img, mode = preprocessor.process(img)
            results = model(processed_img, verbose=False)
            
            detections = []
            status = "awake"
            
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
            
            detected_label = "awake"
            for d in detections:
                 lbl = d['label']
                 if lbl in ["drowsy", "head drop"]:
                     detected_label = lbl
                     break
            
            if detected_label == "awake":
                 for d in detections:
                      lbl = d['label']
                      if lbl in ["yawn", "phone", "distracted"]:
                          detected_label = lbl
                          break
            
            status = detected_label

            # --- Telegram Alert Logic ---
            if user_id and status in ["drowsy", "head drop"]:
                 current_time = time.time()
                 if current_time - last_alert_time > ALERT_COOLDOWN:
                     last_alert_time = current_time
                     
                     # Fire and Forget Alert Task
                     # We need to fetch contacts inside this async loop.
                     from database import SessionLocal
                     from sqlalchemy import select
                     import models
                     from telegram_bot import send_telegram_alert
                     
                     async def send_alerts_async(uid, sts):
                         async with SessionLocal() as db:
                             # Fetch active contacts with telegram_id
                             result = await db.execute(
                                 select(models.EmergencyContact)
                                 .where(
                                     models.EmergencyContact.user_id == uid,
                                     models.EmergencyContact.is_active == True,
                                     models.EmergencyContact.telegram_chat_id != None
                                 )
                             )
                             contacts = result.scalars().all()
                             for contact in contacts:
                                 msg = f"🚨 CẢNH BÁO: Tài xế {contact.owner.full_name if contact.owner else 'của bạn'} đang buồn ngủ/ngất ({sts})! Hãy gọi ngay: {contact.owner.phone_number if contact.owner else ''}!"
                                 await send_telegram_alert(contact.telegram_chat_id, msg)
                     
                     # Create task to avoid blocking inference loop
                     import asyncio
                     asyncio.create_task(send_alerts_async(user_id, status))

            # Send result back
            await websocket.send_json({
                "status": status,
                "detections": detections
            })
            
    except Exception as e:
        print(f"WebSocket Error: {e}")
        try:
            await websocket.close()
        except:
            pass

from fastapi import Depends
from database import get_db, SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
import auth, models, schemas

@router.post("/alert")
async def trigger_manual_alert(
    request: schemas.AlertRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger an alert from Frontend (if FE does detection).
    """
    # Simply reuse the alert logic
    # Fetch user contacts
    from sqlalchemy import select
    from telegram_bot import send_telegram_alert
    
    result = await db.execute(
        select(models.EmergencyContact)
        .where(
            models.EmergencyContact.user_id == current_user.user_id,
            models.EmergencyContact.is_active == True,
            models.EmergencyContact.telegram_chat_id != None
        )
    )
    contacts = result.scalars().all()
    
    sent_count = 0
    
    # Process Image if exists
    photo_bytes = None
    if request.image_base64:
        try:
            import base64
            # Handle possible header like "data:image/jpeg;base64,"
            b64 = request.image_base64
            if "," in b64:
                b64 = b64.split(",")[1]
            photo_bytes = base64.b64decode(b64)
        except Exception as e:
            print(f"Error decoding image: {e}")

    from telegram_bot import send_telegram_alert, send_telegram_photo

    for contact in contacts:
        # Format Google Maps Link
        maps_link = "Không xác định"
        if request.gps_location:
            # Assuming gps_location is "LAT,LNG"
            maps_link = f"https://www.google.com/maps?q={request.gps_location}"
            
        msg = (
            f"🚨 <b>CẢNH BÁO KHẨN CẤP!</b>\n\n"
            f"👤 Tài xế: <b>{current_user.full_name}</b>\n"
            f"⚠️ Trạng thái: <b>{request.event_type}</b> (Nguy hiểm)\n"
            f"📍 Vị trí: <a href='{maps_link}'>Xem trên bản đồ</a>\n"
            f"📞 Gọi ngay: <b>{current_user.phone_number}</b>"
        )
        
        # Note: HTML parse mode is default in python-telegram-bot send_message if specified, 
        # but send_photo caption generally supports it too. 
        # We need to make sure parse_mode='HTML' is passed in telegram_bot.py but we can't change it easily there without verify.
        # Actually, let's keep it simple text if unsure, or try to pass formatting.
        # Check telegram_bot.py: it uses `bot.send_message(..., text=message)` and `bot.send_photo(..., caption=caption)`.
        # Default parse_mode is None. We should update telegram_bot.py to use HTML or Markdown.
        # Wait, I cannot update telegram_bot.py in this step effectively if I'm editing ai_detection.py. 
        # I will stick to plain text with clear formatting first, or assume I can update telegram_bot next.
        # User wants "link to google map", so plain text URL is fine, but HTML <a href> is better.
        # Let's write plain text with URL first to be safe:
        
        msg = (
            f"🚨 CẢNH BÁO KHẨN CẤP!\n\n"
            f"👤 Tài xế: {current_user.full_name}\n"
            f"⚠️ Trạng thái: {request.event_type}\n"
            f"📍 Vị trí: {maps_link}\n"
            f"📞 Gọi ngay: {current_user.phone_number}"
        )
        
        if photo_bytes:
            # Send photo with caption
            await send_telegram_photo(contact.telegram_chat_id, photo_bytes, caption=msg)
        else:
            # Send text only
            await send_telegram_alert(contact.telegram_chat_id, msg)
            
        sent_count += 1
        
    return {"message": f"Alert sent to {sent_count} contacts"}
