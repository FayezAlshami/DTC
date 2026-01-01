"""Verification code repository."""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database.models import VerificationCode, User
from config import config


class VerificationRepository:
    """Repository for verification code operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_code(self, user_id: int) -> str:
        """Create a new verification code."""
        # Delete old unused codes for this user
        from sqlalchemy import delete
        await self.session.execute(
            delete(VerificationCode).where(
                and_(
                    VerificationCode.user_id == user_id,
                    VerificationCode.is_used == False
                )
            )
        )
        await self.session.commit()
        
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        expires_at = datetime.utcnow() + timedelta(minutes=config.VERIFICATION_CODE_EXPIRY_MINUTES)
        
        verification = VerificationCode(
            user_id=user_id,
            code=code,
            expires_at=expires_at
        )
        self.session.add(verification)
        await self.session.commit()
        return code
    
    async def verify_code(self, user_id: int, code: str) -> bool:
        """Verify a code."""
        result = await self.session.execute(
            select(VerificationCode).where(
                and_(
                    VerificationCode.user_id == user_id,
                    VerificationCode.code == code,
                    VerificationCode.is_used == False,
                    VerificationCode.expires_at > datetime.utcnow()
                )
            )
        )
        verification = result.scalar_one_or_none()
        
        if verification:
            verification.is_used = True
            await self.session.commit()
            return True
        return False
    
    async def get_latest_code(self, user_id: int) -> Optional[VerificationCode]:
        """Get the latest verification code for a user."""
        result = await self.session.execute(
            select(VerificationCode).where(
                and_(
                    VerificationCode.user_id == user_id,
                    VerificationCode.is_used == False
                )
            ).order_by(VerificationCode.created_at.desc())
        )
        return result.scalar_one_or_none()

