
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from app.models.user import User


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return password_hash.verify(password, stored_hash)
    except (ValueError, TypeError):
        return False


def register_user(db, username, email, password):
    username = username.strip()
    email = email.strip().lower()

    existing_username = db.scalar(
        select(User).where(
            User.username.ilike(username)
        )
    )

    if existing_username:
        raise ValueError("Username is already registered")

    existing_email = db.scalar(
        select(User).where(
            User.email.ilike(email)
        )
    )

    if existing_email:
        raise ValueError("Email is already registered")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        print("REGISTRATION INTEGRITY ERROR:", repr(exc.orig))
        raise ValueError(
            "Registration failed because of a database constraint."
        ) from exc


def authenticate_user(
    db: Session,
    username_or_email: str,
    password: str,
) -> User | None:
    identifier = username_or_email.strip()

    user = db.scalar(
        select(User).where(
            or_(
                User.username == identifier,
                User.email == identifier.lower(),
            )
        )
    )

    # Legacy OAuth-created users may not have a password hash.
    if user is None or not user.password_hash:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
