"""Authentication router — register, login, profile management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserRegister, UserLogin, Token, UserResponse, UserUpdate
from auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account."""
    # Check if email already in use
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please log in.",
        )

    user = User(
        name=body.name,
        age=body.age,
        gender=body.gender.value,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        phone=body.phone,
        height_cm=body.height_cm,
        activity_level=body.activity_level.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return Token(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "gender": user.gender,
            "age": user.age,
            "height_cm": user.height_cm,
            "activity_level": user.activity_level,
        },
    )


@router.post("/login", response_model=Token)
def login(body: UserLogin, db: Session = Depends(get_db)):
    """Log in and receive a JWT access token."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    token = create_access_token(data={"sub": str(user.id)})
    return Token(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "gender": user.gender,
            "age": user.age,
            "height_cm": user.height_cm,
            "activity_level": user.activity_level,
        },
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the current user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(body: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update mutable profile fields."""
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "activity_level" and hasattr(value, "value"):
            value = value.value
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Soft-delete (deactivate) the current user's account."""
    current_user.is_active = False
    db.commit()
