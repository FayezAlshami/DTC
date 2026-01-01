"""User repository."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.models import User, UserRole
import bcrypt


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, telegram_id: int, email: str, password: str, role: UserRole = UserRole.USER) -> User:
        """Create a new user."""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(
            telegram_id=telegram_id,
            email=email,
            password_hash=password_hash,
            role=role
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def verify_password(self, user: User, password: str) -> bool:
        """Verify user password."""
        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
    
    async def update(self, user: User) -> User:
        """Update user."""
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def is_email_taken(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email is already taken."""
        query = select(User).where(User.email == email)
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_all_users(self, skip: int = 0, limit: int = 100):
        """Get all users (for admin)."""
        result = await self.session.execute(
            select(User).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_students(self, skip: int = 0, limit: int = 100):
        """Get all student users."""
        result = await self.session.execute(
            select(User).where(User.is_student == True).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_non_students(self, skip: int = 0, limit: int = 100):
        """Get all non-student users."""
        result = await self.session.execute(
            select(User).where(User.is_student == False).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def delete(self, user: User):
        """Delete user."""
        await self.session.delete(user)
        await self.session.commit()

