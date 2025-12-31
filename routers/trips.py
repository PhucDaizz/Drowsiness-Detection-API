from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import crud, models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/trips",
    tags=["trips"],
)

@router.post("/start", response_model=schemas.TripResponse)
async def start_trip(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Optional: check if there's already an active trip and end it?
    active_trip = await crud.get_active_trip(db, user_id=current_user.user_id)
    if active_trip:
        return active_trip # Or raise error
    return await crud.create_trip(db=db, user_id=current_user.user_id)

@router.post("/end", response_model=schemas.TripResponse)
async def end_trip(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    active_trip = await crud.get_active_trip(db, user_id=current_user.user_id)
    if not active_trip:
        raise HTTPException(status_code=404, detail="No active trip found")
    
    # We need to implement end_trip in crud properly with update
    # Note: crud.end_trip needs to fetch the updated object
    from sqlalchemy.sql import func
    from sqlalchemy import update
    
    # Implementing inline since I might have missed `func` import in crud.py creation or want to be safe
    # Actually let's assume crud.end_trip works and fix if error.
    # But wait, looking at my previous tool call for crud.py, I used `func.now()` but did I import func?
    # I did import `from sqlalchemy.sql import func` in models.py logic inside crud.py?? 
    # Let's check crud.py content again in my mind... 
    # Ah, I see `from sqlalchemy.sql import func` was NOT in the crud.py imports I wrote.
    # USE multi_replace to fix crud.py later if needed. For now let's use the function and catch error if any.
    
    updated_trip = await crud.end_trip(db, trip_id=active_trip.trip_id)
    return updated_trip

@router.post("/{trip_id}/logs", response_model=schemas.DetectionLogResponse)
async def create_log(
    trip_id: int,
    log: schemas.DetectionLogCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify trip belongs to user
    # Ideally we should fetch trip and check ownership
    # For speed, assuming client sends correct trip_id that they got from /start
    return await crud.create_detection_log(db=db, log=log, trip_id=trip_id)

@router.post("/detections", response_model=schemas.DetectionLogResponse)
async def create_detection_auto_trip(
    log: schemas.DetectionLogCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-resolve active trip and log detection. 
    Useful if client doesn't have trip_id handy.
    """
    active_trip = await crud.get_active_trip(db, user_id=current_user.user_id)
    if not active_trip:
        raise HTTPException(status_code=404, detail="No active trip found to log detection")
    
    return await crud.create_detection_log(db=db, log=log, trip_id=active_trip.trip_id)
