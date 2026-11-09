from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AuthIdentities, Users
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Users).where(Users.email == data.email)):
        raise HTTPException(status_code=409, detail="Ese mail ya está registrado")
    user = Users(
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
    )
    db.add(user)
    db.flush()  # para tener user.id
    # Registramos "mail y contraseña" como una de las formas de entrar de este usuario.
    # Más adelante se le puede sumar la de Google sin tocar la base.
    db.add(AuthIdentities(
        user_id=user.id,
        provider="password",
        provider_user_id=str(user.id),
        email=data.email,
    ))
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # El formulario estándar llama "username" al campo; acá es el mail
    user = db.scalar(select(Users).where(Users.email == form.username))
    # password_hash puede ser None (cuenta creada solo con Google): mismo error genérico
    if user is None or user.password_hash is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Mail o contraseña incorrectos")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(current_user: Users = Depends(get_current_user)):
    return current_user