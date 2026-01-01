"""Authentication service."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repository import UserRepository
from repositories.verification_repository import VerificationRepository
from services.email_service import EmailService
from database.models import User
from email_validator import validate_email, EmailNotValidError


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)
        self.verification_repo = VerificationRepository(session)
        self.email_service = EmailService()
    
    async def validate_email(self, email: str) -> tuple[bool, Optional[str]]:
        """Validate email format."""
        try:
            validate_email(email)
            return True, None
        except EmailNotValidError as e:
            return False, str(e)
    
    async def register_user(self, telegram_id: int, email: str, password: str) -> tuple[bool, Optional[User], Optional[str]]:
        """Register a new user."""
        # Validate email
        is_valid, error = await self.validate_email(email)
        if not is_valid:
            return False, None, f"Invalid email: {error}"
        
        # Check if email is taken
        if await self.user_repo.is_email_taken(email):
            return False, None, "This email is already registered."
        
        # Check if telegram_id is taken
        existing_user = await self.user_repo.get_by_telegram_id(telegram_id)
        if existing_user:
            return False, None, "This Telegram account is already registered."
        
        # Validate password
        if len(password) < 6:
            return False, None, "Password must be at least 6 characters long."
        
        # Create user
        user = await self.user_repo.create(telegram_id, email, password)
        
        # Generate verification code
        # Access the actual ID value from the model instance
        user_id: int = user.id  # type: ignore[assignment]
        code = await self.verification_repo.create_code(user_id)
        
        # Send email
        email_sent = await self.email_service.send_verification_code(email, code)
        if not email_sent:
            return False, None, "Failed to send verification email. Please try again."
        
        return True, user, None
    
    async def verify_code(self, user_id: int, code: str) -> bool:
        """Verify user's code and mark email as verified."""
        is_valid = await self.verification_repo.verify_code(user_id, code)
        if is_valid:
            # Mark email as verified
            user = await self.user_repo.get_by_id(user_id)
            if user:
                user.email_verified = True  # type: ignore[assignment]
                await self.user_repo.update(user)
        return is_valid
    
    async def resend_code(self, user_id: int) -> tuple[bool, Optional[str]]:
        """Resend verification code."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found."
        
        code = await self.verification_repo.create_code(user_id)
        user_email: str = user.email  # type: ignore[assignment]
        email_sent = await self.email_service.send_verification_code(user_email, code)
        if not email_sent:
            return False, "Failed to send verification email. Please try again."
        
        return True, None
    
    async def login(self, email: str, password: str) -> tuple[bool, Optional[User], Optional[str]]:
        """Login user."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            return False, None, "Invalid email or password."
        
        if not await self.user_repo.verify_password(user, password):
            return False, None, "Invalid email or password."
        
        is_active: bool = user.is_active  # type: ignore[assignment]
        if not is_active:
            return False, None, "Your account is deactivated. Please contact support."
        
        return True, user, None

