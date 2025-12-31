# Drowsiness Detection Backend

Backend API for Drowsiness Detection System, built with FastAPI and MySQL. This system tracks driving trips and logs drowsiness events detected by computer vision models (YOLO).

## Features

- **User Management**: 
  - Register, Login (JWT Authentication).
  - Update Profile (Phone, Avatar, Full Name).
- **Emergency Contacts**: 
  - Manage contacts to notify in case of emergency.
- **Trip Management**: 
  - Start and End driving trips.
  - Track trip duration and status.
- **Drowsiness Detection**: 
  - Log events (drowsy, yawn, phone usage, etc.) in real-time.
  - Auto-resolve active trip for detection logs (`POST /trips/detections`).
- **Statistics**: 
  - View trip history.
  - Summary statistics (Total trips, detections, duration).

## Tech Stack

- **Framework**: FastAPI (Python)
- **Database**: MySQL (Async via `aiomysql`)
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens) & Bcrypt
- **Deployment**: Docker & Docker Compose

## Getting Started

### Option 1: Run with Docker (Recommended)

This is the easiest way to run the full stack (Backend + Database).

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/PhucDaizz/Drowsiness-Detection-API
    cd drowsiness_detection_be
    ```

2.  **Build and Run**:
    ```bash
    docker-compose up --build
    ```

3.  **Access the Application**:
    - **API Root**: `http://localhost:8000`
    - **Swagger UI (Docs)**: `http://localhost:8000/docs`
    - **MySQL Database**: `localhost:3308` 
      - User: `root`
      - Password: `phucdai011`
      - Database: `drowsiness_db`

### Option 2: Run Locally (Python)

**Prerequisites**: Python 3.10+, MySQL installed and running.

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    - Ensure MySQL is running on port `3307` (as configured in `database.py`) or update `DATABASE_URL` in `database.py`.
    - Create database `drowsiness_db` (or the app will attempt to create it).

3.  **Run Server**:
    ```bash
    uvicorn main:app --reload
    ```

## API Documentation

Once the server is running, you can access the interactive documentation:

- **Swagger UI**: `/docs` (Test APIs directly in the browser)
- **ReDoc**: `/redoc`

## Project Structure

```
drowsiness_detection_be/
├── routers/            # API Endpoints (Users, Contacts, Trips, Statistics)
├── alembic/            # Database Migrations (Optional/Unused if auto-create is on)
├── auth.py             # Authentication & Password Hashing
├── crud.py             # Database CRUD Operations
├── database.py         # DB Connection & Session Setup
├── main.py             # App Entry Point
├── models.py           # SQLAlchemy Database Models
├── schemas.py          # Pydantic Schemas (Request/Response)
├── Dockerfile          # Docker Image Config
├── docker-compose.yml  # Docker Services Config
└── requirements.txt    # Python Dependencies
```
