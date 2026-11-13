from typing import Annotated
from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel
from uuid import UUID, uuid4

app = FastAPI()

#  Type definitions  #

class UserProfile(BaseModel):
    username: str
    email: str


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
    profile: UserProfile
):
    generated_uuid: UUID | None = None
    while generated_uuid == None:
        generated_uuid = uuid4()
        user: UserProfile | None = mem.get(generated_uuid, None)
        if user:
            generated_uuid = None

    mem[generated_uuid] = profile
    return {"success": True, "detail": "User created !", "data": {"user_id": generated_uuid}}


@app.get("/users/profile")
def get_user(x_user_id: Annotated[str | None, Header()]):
    _header_check(x_user_id)
    user: UserProfile | None = mem.get(x_user_id, None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user_id not found"
        )
    return {"success": True, "detail": "User fetched !", "data": {"user": user}}
    
    
