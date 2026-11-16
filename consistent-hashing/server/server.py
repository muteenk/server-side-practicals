from typing import Annotated
import uuid
from fastapi import Depends, FastAPI, HTTPException, Header, status
from pydantic import BaseModel
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from server.db import lifespan, get_db, UserProfile

app = FastAPI(lifespan=lifespan)



#  Type definitions  #

class UserProfileRequest(BaseModel):
    username: str
    email: str

class UserProfileResponse(UserProfileRequest):
    uuid: UUID

    class Config:
        from_attributes = True


#  Globals  #

mem: dict[UUID, UserProfile] = {}


#  Helpers  #

def _header_check(x_user_id: UUID | None):
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Routing key 'X-User-Id' not provided"
        )


#  Endpoints  #

@app.post("/users/add")
def add_user(
    payload: UserProfileRequest,
    db: Annotated[Session, Depends(get_db)]
):
    user_profile: UserProfile = UserProfile(
        username=payload.username, email=payload.email
    )
    db.add(user_profile)
    db.commit()
    db.refresh(user_profile)
    return {"success": True, "detail": "User created !", "data": {"user_id": user_profile.uuid}}


def _response_payload(*, detail = None, data = None):
    return {
        "success": True,
        "detail": detail,
        "data": data
    }

@app.get("/users/profile")
def get_user(
    x_user_id: Annotated[UUID | None, Header()],
    db: Annotated[Session, Depends(get_db)]
):
    _header_check(x_user_id)
    user: UserProfile | None = None
    user = mem.get(x_user_id, None)

    if user:
        print("CACHE HIT !")
        return _response_payload(detail="User fetched !", data=user)


    stmt = select(UserProfile).where(UserProfile.uuid == x_user_id)
    user = db.scalars(stmt).first()
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User doesn't exist !"
        )
    print("CACHE MISS !")
    mem[user.uuid] = user
    return _response_payload(detail="User fetched !", data=user)
    
