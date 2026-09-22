"""CampaignIQ authentication: password + OTP, or verified Google identity."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.otp_verification import OTPVerification
from app.models.user import User
from app.schemas.auth import GoogleCredentialRequest, OTPVerificationRequest, RegistrationResponse, ResendOTPRequest, TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.google_auth import verify_google_credential
from app.services.otp_service import generate_otp, hash_otp, send_otp_email, verify_otp

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(subject=user.id), user_id=user.id, email=user.email)


async def _issue_otp(user: User, db: AsyncSession) -> None:
    await db.execute(delete(OTPVerification).where(OTPVerification.user_id == user.id, OTPVerification.used_at.is_(None)))
    code = generate_otp()
    db.add(OTPVerification(user_id=user.id, code_hash=hash_otp(code), expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)))
    await db.flush()
    send_otp_email(user.email, code)


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_202_ACCEPTED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    email = str(req.email).strip().lower()
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail={"code": "USER_ALREADY_EXISTS", "message": "An account with this email address already exists"})
    user = User(email=email, password_hash=get_password_hash(req.password), is_active=True, is_verified=False)
    db.add(user)
    await db.flush()
    try:
        await _issue_otp(user, db)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail={"code": "OTP_DELIVERY_UNAVAILABLE", "message": "Verification email could not be sent"}) from exc
    await db.commit()
    return RegistrationResponse(email=email, detail="Verification code sent")


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_registration(req: OTPVerificationRequest, db: AsyncSession = Depends(get_db)):
    email = str(req.email).strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    otp = None if not user else (await db.execute(select(OTPVerification).where(OTPVerification.user_id == user.id, OTPVerification.used_at.is_(None)).order_by(OTPVerification.created_at.desc()).with_for_update())).scalars().first()
    now = datetime.now(timezone.utc)
    if not user or user.is_verified or not otp or otp.expires_at <= now or not verify_otp(req.code, otp.code_hash):
        raise HTTPException(status_code=400, detail={"code": "INVALID_OTP", "message": "Invalid or expired verification code"})
    otp.used_at = now
    user.is_verified = True
    await db.commit()
    return _token_response(user)


@router.post("/resend-otp", response_model=RegistrationResponse, status_code=status.HTTP_202_ACCEPTED)
async def resend_otp(req: ResendOTPRequest, db: AsyncSession = Depends(get_db)):
    email = str(req.email).strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or user.is_verified:
        raise HTTPException(status_code=400, detail={"code": "OTP_NOT_AVAILABLE", "message": "OTP cannot be resent for this account"})
    latest_otp = (await db.execute(
        select(OTPVerification)
        .where(OTPVerification.user_id == user.id)
        .order_by(OTPVerification.created_at.desc())
    )).scalars().first()
    now = datetime.now(timezone.utc)
    if latest_otp and latest_otp.created_at > now - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS):
        raise HTTPException(
            status_code=429,
            detail={"code": "OTP_RESEND_RATE_LIMITED", "message": "Please wait before requesting another verification code"},
            headers={"Retry-After": str(settings.OTP_RESEND_COOLDOWN_SECONDS)},
        )
    try:
        await _issue_otp(user, db)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail={"code": "OTP_DELIVERY_UNAVAILABLE", "message": "Verification email could not be sent"}) from exc
    return RegistrationResponse(email=email, detail="Verification code sent")


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    email = str(req.email).strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password"}, headers={"WWW-Authenticate": "Bearer"})
    if not user.is_verified:
        raise HTTPException(status_code=403, detail={"code": "EMAIL_NOT_VERIFIED", "message": "Verify your email before logging in"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"code": "USER_INACTIVE", "message": "User account has been deactivated"})
    return _token_response(user)


@router.post("/google", response_model=TokenResponse)
async def google_login(req: GoogleCredentialRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = verify_google_credential(req.credential)
    except Exception as exc:
        raise HTTPException(status_code=401, detail={"code": "INVALID_GOOGLE_CREDENTIAL", "message": "Google identity could not be verified"}) from exc
    subject = claims.get("sub")
    claimed_email = claims.get("email")
    if not isinstance(subject, str) or not subject or not isinstance(claimed_email, str) or not claimed_email.strip() or claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail={"code": "INVALID_GOOGLE_CREDENTIAL", "message": "Google identity could not be verified"})
    email = claimed_email.strip().lower()
    user = (await db.execute(select(User).where(User.google_sub == subject))).scalar_one_or_none()
    if not user:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        if user.google_sub and user.google_sub != subject:
            raise HTTPException(status_code=409, detail={"code": "GOOGLE_ID_CONFLICT", "message": "Google identity is already linked to another account"})
        if not user.is_active:
            raise HTTPException(status_code=403, detail={"code": "USER_INACTIVE", "message": "User account has been deactivated"})
        user.google_sub = subject
        user.is_verified = True
    else:
        user = User(email=email, google_sub=subject, password_hash=None, is_active=True, is_verified=True)
        db.add(user)
        await db.flush()
    await db.commit()
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
