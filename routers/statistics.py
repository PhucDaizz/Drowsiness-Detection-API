from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime
import crud, models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
)

@router.get("/trips", response_model=List[schemas.TripSummary])
async def get_my_trips(
    limit: int = 10,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's trip history (summary only, no logs)"""
    trips = await crud.get_user_trips(db, user_id=current_user.user_id, limit=limit)
    
    result = []
    for trip in trips:
        # Get count only
        total_detections = await crud.get_trip_detection_count(db, trip_id=trip.trip_id)
        
        duration_minutes = None
        if trip.end_time and trip.start_time:
            duration_minutes = int((trip.end_time - trip.start_time).total_seconds() / 60)
        
        trip_data = schemas.TripSummary(
            trip_id=trip.trip_id,
            user_id=trip.user_id,
            start_time=trip.start_time,
            end_time=trip.end_time,
            status=trip.status,
            total_detections=total_detections, # Optimized count
            duration_minutes=duration_minutes
        )
        result.append(trip_data)
    
    return result

@router.get("/trips/{trip_id}", response_model=schemas.TripWithLogs)
async def get_trip_details(
    trip_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific trip including all detection logs"""
    trip = await crud.get_trip(db, trip_id=trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
        
    # Ensure user owns the trip
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this trip")
    
    logs = await crud.get_trip_logs(db, trip_id=trip.trip_id)
    
    duration_minutes = None
    if trip.end_time and trip.start_time:
        duration_minutes = int((trip.end_time - trip.start_time).total_seconds() / 60)
    
    return schemas.TripWithLogs(
        trip_id=trip.trip_id,
        user_id=trip.user_id,
        start_time=trip.start_time,
        end_time=trip.end_time,
        status=trip.status,
        logs=[schemas.DetectionLogResponse.from_orm(log) for log in logs],
        total_detections=len(logs),
        duration_minutes=duration_minutes
    )

@router.get("/summary", response_model=schemas.UserStatistics)
async def get_statistics_summary(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get overall statistics for the user with optimized response"""
    # 1. Get all trips for counts and duration
    # Note: For huge data, this should be optimized to SQL Aggregation (SUM(duration), COUNT(*))
    # But for now, python iteration for duration is acceptable if not excessive.
    # Let's keep it simple: limit 1000 for stats is fine for this scale, or fetch all but only necessary columns?
    # Actually, let's just fetch all trips for now to be accurate on total_duration/trips
    trips = await crud.get_user_trips(db, user_id=current_user.user_id, limit=9999) 
    
    total_trips = len(trips)
    total_duration_minutes = 0
    
    for trip in trips:
        if trip.end_time and trip.start_time:
            duration = int((trip.end_time - trip.start_time).total_seconds() / 60)
            total_duration_minutes += duration

    # 2. Get Total Detections (SQL Optimized)
    total_detections = await crud.get_user_detection_count(db, user_id=current_user.user_id)

    # 3. Get Breakdown (SQL Optimized)
    detection_breakdown = await crud.get_detection_breakdown(db, user_id=current_user.user_id)

    # 4. Recent Trips (Last 10) - Map to Summary (No detailed logs)
    recent_trips_data = []
    # trips is already ordered DESC from crud.get_user_trips
    recent_trips = trips[:10]
    
    for trip in recent_trips:
        # We need individual trip detection count. 
        # Making 10 queries is better than fetching 1000s of log rows.
        trip_detection_count = await crud.get_trip_detection_count(db, trip_id=trip.trip_id)
        
        duration_minutes = None
        if trip.end_time and trip.start_time:
            duration_minutes = int((trip.end_time - trip.start_time).total_seconds() / 60)
            
        summary = schemas.TripSummary(
            trip_id=trip.trip_id,
            user_id=trip.user_id,
            start_time=trip.start_time,
            end_time=trip.end_time,
            status=trip.status,
            total_detections=trip_detection_count,
            duration_minutes=duration_minutes
        )
        recent_trips_data.append(summary)
    
    return schemas.UserStatistics(
        total_trips=total_trips,
        total_detections=total_detections,
        total_duration_minutes=total_duration_minutes,
        detection_breakdown=detection_breakdown,
        recent_trips=recent_trips_data
    )
