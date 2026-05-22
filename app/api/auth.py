from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(payload: RegisterRequest) -> dict[str, str]:
    return {"status": "stub", "email": payload.email}


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, str]:
    return {"access_token": f"local-dev-token-for-{payload.email}", "token_type": "bearer"}

