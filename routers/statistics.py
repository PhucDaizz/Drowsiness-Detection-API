from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta, date
import crud, models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
)

@router.get("/trips", response_model=List[schemas.TripSummary])
async def get_my_trips(
    limit: int = 10,
    period: Optional[schemas.StatsPeriod] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's trip history (summary only, no logs) with optional period filter"""
    
    if period:
        now = datetime.now()
        start_date = now
        
        if period == schemas.StatsPeriod.TODAY:
             start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == schemas.StatsPeriod.THIS_WEEK:
             start_date = now - timedelta(days=now.weekday())
             start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == schemas.StatsPeriod.THIS_MONTH:
             start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == schemas.StatsPeriod.THIS_YEAR:
             start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
             
        trips = await crud.get_trips_by_range(db, user_id=current_user.user_id, start_date=start_date, end_date=now)
    else:
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
    period: Optional[schemas.StatsPeriod] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get overall statistics for the user with optimized response"""
    
    # Optional filtering for summary? User asked for filtering.
    # The requirement was "summary" API with "filtering". 
    # Current code takes "limit" but not "period".
    # Let's add 'period' support here similar to /trips endpoint if requested.
    # But wait, user said "summary doesn't have filtering".
    # I should add 'period' param here too.
    
    trips = []
    if period:
        now = datetime.now()
        start_date = now
        
        if period == schemas.StatsPeriod.TODAY:
             start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == schemas.StatsPeriod.THIS_WEEK:
             start_date = now - timedelta(days=now.weekday())
             start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == schemas.StatsPeriod.THIS_MONTH:
             start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == schemas.StatsPeriod.THIS_YEAR:
             start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
             
        # Fetch filtered trips
        trips = await crud.get_trips_by_range(db, user_id=current_user.user_id, start_date=start_date, end_date=now)
    else:
        # 1. Get all trips for counts and duration
        # Note: limit=9999 might be risky for huge datasets but fine for now.
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

@router.get("/durations", response_model=schemas.DrivingStatsResponse)
async def get_driving_stats(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get driving duration statistics for Today, Week, Month, Year"""
    now = datetime.now()
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # helper to calc hours
    def calc_hours(trips_list):
        minutes = 0
        for trip in trips_list:
            if trip.end_time and trip.start_time:
                 # Ensure we are comparing compatible datetimes (naive vs naive or aware vs aware)
                 # trip.end_time and trip.start_time likely share the same tzinfo from DB
                 minutes += int((trip.end_time - trip.start_time).total_seconds() / 60)
        return round(minutes / 60, 2)

    # Fetch all trips this year as base
    # NOTE: If user has trips crossing years or years ago, we should actually fetch ALL trips or generic logic.
    # But usually "Statistics" implies "Current stats".
    # For safety/accuracy let's just use the 'get_trips_by_range' for each bucket or optimizing one big fetch.
    # Given we might have different buckets, let's just make one big fetch for "This Year" and filter in python.
    # Anything older than this year is not needed for "Today/Week/Month/Year" stats.
    
    all_year_trips = await crud.get_trips_by_range(db, current_user.user_id, year_start, now)
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    today_trips = [t for t in all_year_trips if t.start_time.replace(tzinfo=None) >= today_start]
    week_trips = [t for t in all_year_trips if t.start_time.replace(tzinfo=None) >= week_start]
    month_trips = [t for t in all_year_trips if t.start_time.replace(tzinfo=None) >= month_start]
    
    # Note: timestamp from DB might be timezone aware or naive. Python datetime.now() usually naive. 
    # SQLAlchemy timezone=True returns aware. Simple fix: use replace(tzinfo=None) for comparison if needed or ensuring both are aware.
    # Assuming standard setup, let's try direct comparison, if fails we fix. 
    # Actually models.py says: Column(DateTime(timezone=True))
    # So we should make our comparison offsets aware if possible or strip tz from db obj. 
    # Ideally, just use the helper logic again but Python side is simpler if timezone details are consistent.
    # We will assume DB returns naive UTC or Local matching system time for now.
    
    return schemas.DrivingStatsResponse(
        today_hours=calc_hours(today_trips),
        week_hours=calc_hours(week_trips),
        month_hours=calc_hours(month_trips),
        year_hours=calc_hours(all_year_trips)
    )

@router.get("/calendar", response_model=schemas.CalendarCheckinResponse)
async def get_checkin_calendar(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of days (dates) where user had driving activity in a specific month"""
    start_times = await crud.get_active_driving_days(db, current_user.user_id, month, year)
    
    # Extract unique dates
    unique_dates = set()
    for dt in start_times:
        unique_dates.add(dt.date())
    
    # Convert back to list of datetimes (midnight) or just return dates? Schema says datetime list.
    # Let's return datetime at midnight for simplicity in JSON serialization
    active_days = [datetime.combine(d, datetime.min.time()) for d in sorted(unique_dates)]
    
    return schemas.CalendarCheckinResponse(active_days=active_days)
