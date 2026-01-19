# API Documentation - Drowsiness Detection System

## General Information
- **Base URL:** `http://localhost:8000` (or your deployed server IP)
- **Base WebSocket URL:** `ws://localhost:8000`
- **Authentication:** All protected routes require a Bearer Token in the Header: `Authorization: Bearer <your_token>`.

---

## 1. Authentication (Users)

### 1.1. Register User
- **Endpoint:** `POST /users/register`
- **Description:** Register a new user account.
- **Request Body (JSON):**
  ```json
  {
    "email": "user@example.com",
    "password": "your_password",
    "full_name": "Nguyen Van A",
    "phone_number": "0987654321",
    "avatar_url": "link_to_image" // Optional
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "email": "user@example.com",
    "full_name": "Nguyen Van A",
    "phone_number": "0987654321",
    "avatar_url": "link_to_image",
    "user_id": 1,
    "created_at": "2024-01-01T12:00:00"
  }
  ```

### 1.2. Login (Get Token)
- **Endpoint:** `POST /users/token`
- **Description:** Login to get access token.
- **Request Body (Form Data - x-www-form-urlencoded):**
  - `username`: user@example.com (Note: Field name is 'username' but value is email)
  - `password`: your_password
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer"
  }
  ```

### 1.3. Get My Profile
- **Endpoint:** `GET /users/me`
- **Headers:** `Authorization: Bearer <token>`
- **Response:**
  ```json
  {
    "email": "user@example.com",
    "full_name": "Nguyen Van A",
    "phone_number": "0987654321",
    "avatar_url": null,
    "user_id": 1,
    "created_at": "..."
  }
  ```

### 1.4. Update Profile
- **Endpoint:** `PUT /users/me`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body (JSON):** (Send only fields you want to update)
  ```json
  {
    "full_name": "Nguyen Van B", // Optional
    "phone_number": "0123456789", // Optional
    "avatar_url": "new_link" // Optional
  }
  ```
- **Response:** Updated user object.

### 1.5. Forgot Password
- **Endpoint:** `POST /users/forgot-password`
- **Request Body:**
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response:** `{"message": "Password reset code sent to email"}`

### 1.6. Reset Password
- **Endpoint:** `POST /users/reset-password`
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "new_password": "new_secure_password",
    "code": "123456" // Code received in email
  }
  ```
- **Response:** `{"message": "Password updated successfully"}`

---

## 2. Emergency Contacts

### 2.1. Add Contact
- **Endpoint:** `POST /contacts/`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "name": "Mom",
    "phone_number": "0909090909",
    "is_active": true
  }
  ```
- **Response:** Created contact object.

### 2.2. Get List Contacts
- **Endpoint:** `GET /contacts/`
- **Headers:** `Authorization: Bearer <token>`
- **Response:** Array of contacts.

### 2.3. Update/Delete Contact
- **Update:** `PUT /contacts/{contact_id}`
- **Delete:** `DELETE /contacts/{contact_id}`

---

## 3. Trips (Hành trình)

### 3.1. Start Trip
- **Endpoint:** `POST /trips/start`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Call this when user presses "Start Driving".
- **Response:**
  ```json
  {
    "trip_id": 10,
    "user_id": 1,
    "start_time": "2024-01-01T12:00:00",
    "status": "ONGOING"
  }
  ```

### 3.2. End Trip
- **Endpoint:** `POST /trips/end`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Call this when user finishes driving. It will close the currently active trip.
- **Response:** Updated trip object with `end_time`.

### 3.3. Log Detection (Auto Trip Resolve)
- **Endpoint:** `POST /trips/detections`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Call this mainly from Backend's internal logic OR if App handles detection locally and wants to sync. Since we use WebSocket for detection, the Server usually handles logging. **(Frontend might not need to call this manually if using WebSocket)**.

---

## 4. AI Detection (Real-time) - IMPORTANT 🚀

### 4.1. WebSocket Detection (Recommended)
This is the core feature for real-time monitoring.

- **URL:** `ws://localhost:8000/ai/ws/detect`
- **Method:** WebSocket
- **Handshake:** Connection established.
- **Data Flow:**
    1.  **Frontend:** Captures frame -> Converts to Bytes (Blob/ArrayBuffer) -> Sends to WebSocket.
    2.  **Server:** Receives -> Preprocesses -> Predicts -> Responds.
- **Response (JSON):**
  ```json
  {
    "status": "drowsy", // "awake", "drowsy", "yawn", "phone", "head drop", "distracted"
    "detections": [
      {
        "label": "drowsy",
        "confidence": 0.88,
        "box": [100, 200, 300, 400] // [x1, y1, x2, y2]
      }
    ]
  }
  ```
- **Frontend Logic:**
    - If `status` == "drowsy" or "head drop" => **Play Alarm Sound 🚨**
    - Draw boxes on camera overlay using `box` coordinates.

### 4.2. HTTP Detection (One-shot)
- **Endpoint:** `POST /ai/detect`
- **Content-Type:** `multipart/form-data`
- **Body:** `file` (Image file)
- **Response:** Same JSON structure as WebSocket.

---

## 5. Statistics (Thống kê)

### 5.1. User Summary Dashboard
- **Endpoint:** `GET /statistics/summary`
- **Headers:** `Authorization: Bearer <token>`
- **Optional Param:** `?period=TODAY` (or `THIS_WEEK`, `THIS_MONTH`, `THIS_YEAR`)
- **Response:**
  ```json
  {
    "total_trips": 5,
    "total_detections": 12,
    "total_duration_minutes": 150,
    "detection_breakdown": {
      "drowsy": 5,
      "yawn": 2,
      "phone": 5
    },
    "recent_trips": [ ...list of 10 recent trips... ]
  }
  ```

### 5.2. Driving Duration Stats
- **Endpoint:** `GET /statistics/durations`
- **Headers:** `Authorization: Bearer <token>`
- **Response:**
  ```json
  {
    "today_hours": 1.5,
    "week_hours": 10.2,
    "month_hours": 45.0,
    "year_hours": 120.5
  }
  ```

### 5.3. Calendar Check-ins
- **Endpoint:** `GET /statistics/calendar`
- **Headers:** `Authorization: Bearer <token>`
- **Query Params:** `?month=1&year=2024`
- **Response:**
  ```json
  {
    "active_days": [
      "2024-01-01T00:00:00",
      "2024-01-03T00:00:00"
    ]
  }
  ```
- **FE Usage:** Highlight these dates on the calendar UI.

### 5.4. Trip Detail with Logs
- **Endpoint:** `GET /statistics/trips/{trip_id}`
- **Headers:** `Authorization: Bearer <token>`
- **Response:** Full trip info + array of all incident logs with timestamps and locations.
