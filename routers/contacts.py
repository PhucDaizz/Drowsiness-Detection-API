from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import crud, models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/contacts",
    tags=["contacts"],
)

@router.post("/", response_model=schemas.ContactResponse)
async def create_contact(
    contact: schemas.ContactCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.create_contact(db=db, contact=contact, user_id=current_user.user_id)

@router.get("/", response_model=List[schemas.ContactResponse])
async def read_contacts(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_contacts(db=db, user_id=current_user.user_id)

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    success = await crud.delete_contact(db=db, contact_id=contact_id, user_id=current_user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"ok": True}

@router.put("/{contact_id}", response_model=schemas.ContactResponse)
async def update_contact(
    contact_id: int,
    contact_update: schemas.ContactUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    updated_contact = await crud.update_contact(
        db=db, 
        contact_id=contact_id, 
        contact_update=contact_update, 
        user_id=current_user.user_id
    )
    if not updated_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated_contact
