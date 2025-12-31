from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.sql import func
import models, schemas
from auth import get_password_hash
from datetime import datetime


# --- User CRUD ---
async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        full_name=user.full_name,
        phone_number=user.phone_number,
        avatar_url=user.avatar_url
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate):
    query = (
        update(models.User)
        .where(models.User.user_id == user_id)
        .values(**user_update.model_dump(exclude_unset=True))
    )
    await db.execute(query)
    await db.commit()
    
    result = await db.execute(select(models.User).where(models.User.user_id == user_id))
    return result.scalars().first()


# --- Contact CRUD ---
async def get_contacts(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.EmergencyContact).where(models.EmergencyContact.user_id == user_id))
    return result.scalars().all()

async def create_contact(db: AsyncSession, contact: schemas.ContactCreate, user_id: int):
    db_contact = models.EmergencyContact(**contact.model_dump(), user_id=user_id)
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    await db.refresh(db_contact)
    return db_contact

async def update_contact(db: AsyncSession, contact_id: int, contact_update: schemas.ContactUpdate, user_id: int):
    # Ensure contact belongs to user
    result = await db.execute(
        select(models.EmergencyContact)
        .where(
            models.EmergencyContact.contact_id == contact_id,
            models.EmergencyContact.user_id == user_id
        )
    )
    contact = result.scalars().first()
    if not contact:
        return None

    query = (
        update(models.EmergencyContact)
        .where(models.EmergencyContact.contact_id == contact_id)
        .values(**contact_update.model_dump(exclude_unset=True))
    )
    await db.execute(query)
    await db.commit()
    
    result = await db.execute(select(models.EmergencyContact).where(models.EmergencyContact.contact_id == contact_id))
    return result.scalars().first()


async def delete_contact(db: AsyncSession, contact_id: int, user_id: int):
    result = await db.execute(select(models.EmergencyContact).where(
        models.EmergencyContact.contact_id == contact_id,
        models.EmergencyContact.user_id == user_id
    ))
    contact = result.scalars().first()
    if contact:
        await db.delete(contact)
        await db.commit()
        return True
    return False

# --- Trip CRUD ---
async def create_trip(db: AsyncSession, user_id: int):
    db_trip = models.Trip(user_id=user_id, status=models.TripStatus.ONGOING)
    db.add(db_trip)
    await db.commit()
    await db.refresh(db_trip)
    return db_trip

async def get_active_trip(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.Trip).where(
        models.Trip.user_id == user_id,
        models.Trip.status == models.TripStatus.ONGOING
    ).order_by(models.Trip.start_time.desc()))
    return result.scalars().first()

async def get_trip(db: AsyncSession, trip_id: int):
    result = await db.execute(select(models.Trip).where(models.Trip.trip_id == trip_id))
    return result.scalars().first()

async def end_trip(db: AsyncSession, trip_id: int):

    query = (
        update(models.Trip)
        .where(models.Trip.trip_id == trip_id)
        .values(status=models.TripStatus.FINISHED, end_time=func.now())
    )
    await db.execute(query)
    await db.commit()
    
    # Return updated trip
    result = await db.execute(select(models.Trip).where(models.Trip.trip_id == trip_id))
    return result.scalars().first()

# --- Log CRUD ---
async def create_detection_log(db: AsyncSession, log: schemas.DetectionLogCreate, trip_id: int):
    db_log = models.DetectionLog(**log.model_dump(), trip_id=trip_id)
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    return db_log

# --- Statistics CRUD ---
async def get_user_trips(db: AsyncSession, user_id: int, limit: int = 10):
    result = await db.execute(
        select(models.Trip)
        .where(models.Trip.user_id == user_id)
        .order_by(models.Trip.start_time.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def get_trip_logs(db: AsyncSession, trip_id: int):
    result = await db.execute(
        select(models.DetectionLog)
        .where(models.DetectionLog.trip_id == trip_id)
        .order_by(models.DetectionLog.timestamp)
    )
    return result.scalars().all()

async def get_user_detection_count(db: AsyncSession, user_id: int):
    # Count all detections across all user trips
    from sqlalchemy import func as sql_func
    result = await db.execute(
        select(sql_func.count(models.DetectionLog.log_id))
        .join(models.Trip)
        .where(models.Trip.user_id == user_id)
    )
    return result.scalar() or 0

async def get_detection_breakdown(db: AsyncSession, user_id: int):
    # Group by event_type
    from sqlalchemy import func as sql_func
    result = await db.execute(
        select(models.DetectionLog.event_type, sql_func.count(models.DetectionLog.log_id))
        .join(models.Trip)
        .where(models.Trip.user_id == user_id)
        .group_by(models.DetectionLog.event_type)
    )
    return dict(result.all())

async def get_trip_detection_count(db: AsyncSession, trip_id: int):
    from sqlalchemy import func as sql_func
    result = await db.execute(
        select(sql_func.count(models.DetectionLog.log_id))
        .where(models.DetectionLog.trip_id == trip_id)
    )
    return result.scalar() or 0
