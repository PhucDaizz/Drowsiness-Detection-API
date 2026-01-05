from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import crud, models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@router.post("/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await crud.create_user(db=db, user=user)

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # OAuth2PasswordRequestForm uses 'username' field, we treat it as email
    user = await crud.get_user_by_email(db, email=form_data.username) 
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

from pydantic import BaseModel, EmailStr
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str
    code: str  # For simulation purposes

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
import os
import secrets
from typing import Dict

# Dictionary to store reset codes temporarily (In memory for simplicity, use Redis for production)
reset_codes: Dict[str, str] = {}

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "cordelia46@ethereal.email"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "EEBHFkrBseztNUr3Br"),
    MAIL_FROM = os.getenv("MAIL_FROM", "phucdai@gmail.com"),
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.ethereal.email"),
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Sends a real password reset code via Email (SMTP).
    """
    user = await crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Generate random 6-digit code
    code = str(secrets.randbelow(1000000)).zfill(6)
    
    # Store code in memory (Valid until server restart or overwritten)
    reset_codes[request.email] = code
    
    html = f"""
    <p>Your password reset code is: <strong>{code}</strong></p>
    <p>Please enter this code in the app to reset your password.</p>
    """

    message = MessageSchema(
        subject="Drowsiness Detection - Password Reset",
        recipients=[request.email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
    except Exception as e:
         print(f"Error sending email: {e}")
         raise HTTPException(status_code=500, detail="Failed to send email")

    return {"message": "Password reset code sent to email"}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Resets user password using the code.
    """
    stored_code = reset_codes.get(request.email)
    if not stored_code or stored_code != request.code:
         raise HTTPException(status_code=400, detail="Invalid or expired verification code")
         
    # Clean up used code
    del reset_codes[request.email]

    user = await crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password Logic
    # We need a dedicated update_password function in CRUD or reuse dynamic update_user if password field allowed
    # UserUpdate schema doesn't have password. Let's add specific logic here.
    new_hash = auth.get_password_hash(request.new_password)
    
    from sqlalchemy import update
    query = (
        update(models.User)
        .where(models.User.user_id == user.user_id)
        .values(password_hash=new_hash)
    )
    await db.execute(query)
    await db.commit()
    
    return {"message": "Password updated successfully"}

@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
async def update_users_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.update_user(db=db, user_id=current_user.user_id, user_update=user_update)
