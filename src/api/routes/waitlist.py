from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr
from typing import Dict
from datetime import datetime

from src.db.base import get_db
from src.db.queries.waitlist import create_waitlist_entry, get_waitlist_entry

router = APIRouter(
    prefix="/api/v1/waitlist",
    tags=["waitlist"],
    responses={
        400: {
            "description": "Invalid email",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email format"}
                }
            }
        }
    }
)

class WaitlistRequest(BaseModel):
    email: EmailStr

@router.post(
    "",
    response_model=Dict[str, str],
    responses={
        200: {
            "description": "Waitlist response",
            "content": {
                "application/json": {
                    "examples": {
                        "new_entry": {
                            "value": {"message": "You've successfully joined waitlist"}
                        },
                        "existing": {
                            "value": {"message": "You've already joined waitlist"}
                        }
                    }
                }
            }
        }
    }
)
async def join_waitlist(
    request: Request,
    waitlist_request: WaitlistRequest
) -> Dict[str, str]:
    """
    Add user to waitlist.
    
    Stores email and request metadata in waitlist_users table.
    Returns appropriate message based on whether email already exists.
    """
    with get_db() as conn:
        # Check if email already exists
        existing_entry = get_waitlist_entry(conn, waitlist_request.email)
        if existing_entry:
            return {"message": "You've already joined waitlist"}
        
        # Collect request metadata
        metadata = {
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "referrer": request.headers.get("referer"),
            "timestamp": datetime.utcnow()
        }
        
        # Create new waitlist entry
        create_waitlist_entry(conn, waitlist_request.email, metadata)
        return {"message": "You've successfully joined waitlist"}
