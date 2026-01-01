"""Subject repository."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database.models import Subject, Specialization


class SubjectRepository:
    """Repository for subject operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, subject: Subject) -> Subject:
        """Create a new subject."""
        self.session.add(subject)
        await self.session.commit()
        await self.session.refresh(subject)
        return subject
    
    async def get_by_id(self, subject_id: int) -> Optional[Subject]:
        """Get subject by ID."""
        result = await self.session.execute(
            select(Subject)
            .options(selectinload(Subject.specialization))
            .where(Subject.id == subject_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[Subject]:
        """Get subject by code."""
        result = await self.session.execute(
            select(Subject).where(Subject.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_specialization(self, specialization_id: int, active_only: bool = True) -> List[Subject]:
        """Get all subjects for a specialization."""
        query = select(Subject).where(Subject.specialization_id == specialization_id)
        if active_only:
            query = query.where(Subject.is_active == True)
        query = query.order_by(Subject.display_order.asc(), Subject.name.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_all(self, active_only: bool = False) -> List[Subject]:
        """Get all subjects."""
        query = select(Subject).options(selectinload(Subject.specialization))
        if active_only:
            query = query.where(Subject.is_active == True)
        query = query.order_by(Subject.display_order.asc(), Subject.name.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update(self, subject: Subject) -> Subject:
        """Update subject."""
        await self.session.commit()
        await self.session.refresh(subject)
        return subject
    
    async def delete(self, subject: Subject):
        """Delete subject."""
        await self.session.delete(subject)
        await self.session.commit()
    
    async def deactivate(self, subject_id: int) -> bool:
        """Deactivate a subject."""
        result = await self.session.execute(
            update(Subject)
            .where(Subject.id == subject_id)
            .values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def activate(self, subject_id: int) -> bool:
        """Activate a subject."""
        result = await self.session.execute(
            update(Subject)
            .where(Subject.id == subject_id)
            .values(is_active=True)
        )
        await self.session.commit()
        return result.rowcount > 0

