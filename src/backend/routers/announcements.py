"""
Announcements API router for managing school announcements
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from ..database import announcements_collection
from .auth import get_current_user

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

# Pydantic models
class AnnouncementCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    start_date: Optional[datetime] = None
    expiration_date: datetime

class AnnouncementUpdate(BaseModel):
    message: Optional[str] = Field(None, min_length=1, max_length=500)
    start_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None

class Announcement(BaseModel):
    id: str = Field(alias="_id")
    message: str
    start_date: Optional[datetime]
    expiration_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str
        }

@router.get("/", response_model=List[Announcement])
async def get_announcements():
    """Get all active announcements"""
    now = datetime.utcnow()
    query = {
        "expiration_date": {"$gt": now}
    }
    # Also check start_date if it exists
    query["$or"] = [
        {"start_date": None},
        {"start_date": {"$lte": now}}
    ]
    
    announcements = list(announcements_collection.find(query))
    for announcement in announcements:
        announcement["id"] = str(announcement["_id"])
    return announcements

@router.get("/all", response_model=List[Announcement])
async def get_all_announcements(current_user: dict = Depends(get_current_user)):
    """Get all announcements (admin only)"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can view all announcements"
        )
    
    announcements = list(announcements_collection.find({}))
    for announcement in announcements:
        announcement["id"] = str(announcement["_id"])
    return announcements

@router.post("/", response_model=Announcement)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new announcement (admin only)"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can create announcements"
        )
    
    now = datetime.utcnow()
    announcement = {
        "message": announcement_data.message,
        "start_date": announcement_data.start_date,
        "expiration_date": announcement_data.expiration_date,
        "created_at": now,
        "updated_at": now
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = result.inserted_id
    announcement["id"] = str(result.inserted_id)
    
    return announcement

@router.put("/{announcement_id}", response_model=Announcement)
async def update_announcement(
    announcement_id: str,
    announcement_data: AnnouncementUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an announcement (admin only)"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can update announcements"
        )
    
    try:
        object_id = ObjectId(announcement_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid announcement ID"
        )
    
    # Build update data
    update_data = {"updated_at": datetime.utcnow()}
    if announcement_data.message is not None:
        update_data["message"] = announcement_data.message
    if announcement_data.start_date is not None:
        update_data["start_date"] = announcement_data.start_date
    if announcement_data.expiration_date is not None:
        update_data["expiration_date"] = announcement_data.expiration_date
    
    result = announcements_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    announcement = announcements_collection.find_one({"_id": object_id})
    announcement["id"] = str(announcement["_id"])
    return announcement

@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an announcement (admin only)"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can delete announcements"
        )
    
    try:
        object_id = ObjectId(announcement_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid announcement ID"
        )
    
    result = announcements_collection.delete_one({"_id": object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    return {"message": "Announcement deleted successfully"}