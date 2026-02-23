"""
Authentication API endpoints.

Handles user signup, login, OAuth, and token management.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from jose import jwt
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from config import settings

limiter = Limiter(key_func=get_remote_address)
from models.automation_config import AutomationConfig
from models.user import User
from schemas.user import (
    GoogleOAuthRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

# Google OAuth endpoints
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

logger = logging.getLogger(__name__)

router = APIRouter()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token (7 day expiry)."""
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def signup(request: Request, response: Response, user_data: UserCreate, db: DbSession) -> TokenResponse:
    """
    Create a new user account.

    Creates user and default automation config, returns JWT token.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        name=user_data.name,
        phone=user_data.phone,
    )
    db.add(user)
    await db.flush()  # Get user ID

    # Create default automation config
    config = AutomationConfig(host_id=user.id)
    db.add(config)

    await db.commit()
    await db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    # Generate tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, login_data: UserLogin, db: DbSession) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    logger.info(f"User logged in: {user.email}")

    # Generate tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/oauth/google", response_model=TokenResponse)
@limiter.limit("5/minute")
async def google_oauth(request: Request, response: Response, oauth_data: GoogleOAuthRequest, db: DbSession) -> TokenResponse:
    """
    Authenticate via Google OAuth.

    Exchanges authorization code for user info and creates/retrieves user.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Exchange authorization code for access token
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": oauth_data.code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": oauth_data.redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=10.0,
            )

            if token_response.status_code != 200:
                logger.error(f"Google token exchange failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code",
                )

            token_data = token_response.json()
            google_access_token = token_data.get("access_token")

            if not google_access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from Google",
                )

            # Step 2: Fetch user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
                timeout=10.0,
            )

            if userinfo_response.status_code != 200:
                logger.error(f"Google userinfo fetch failed: {userinfo_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch user info from Google",
                )

            userinfo = userinfo_response.json()
            email = userinfo.get("email")
            name = userinfo.get("name", email.split("@")[0] if email else "User")

            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email received from Google",
                )

    except httpx.RequestError as e:
        logger.error(f"HTTP request error during Google OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to communicate with Google OAuth service",
        )

    # Step 3: Create or retrieve user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Create new user (no password since using OAuth)
        user = User(
            email=email,
            hashed_password="",  # OAuth users don't have passwords
            name=name,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create default automation config
        config = AutomationConfig(host_id=user.id)
        db.add(config)

        await db.commit()
        await db.refresh(user)
        logger.info(f"New OAuth user registered: {email}")
    else:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        logger.info(f"OAuth user logged in: {email}")

    # Step 4: Return JWT tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: DbSession) -> TokenResponse:
    """
    Refresh an access token using a refresh token.

    Send the refresh token in the Authorization header as Bearer token.
    """
    from fastapi.security import HTTPBearer
    from jose import JWTError

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    from uuid import UUID
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """
    Get current authenticated user's information.
    """
    return UserResponse.model_validate(current_user)
