"""Specialization repository."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database.models import Specialization


class SpecializationRepository:
    """Repository for specialization operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, specialization: Specialization) -> Specialization:
        """Create a new specialization."""
        self.session.add(specialization)
        await self.session.commit()
        await self.session.refresh(specialization)
        return specialization
    
    async def get_by_id(self, specialization_id: int) -> Optional[Specialization]:
        """Get specialization by ID."""
        result = await self.session.execute(
            select(Specialization).where(Specialization.id == specialization_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Specialization]:
        """Get specialization by name."""
        result = await self.session.execute(
            select(Specialization).where(Specialization.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_all_active(self) -> List[Specialization]:
        """Get all active specializations ordered by display_order."""
        result = await self.session.execute(
            select(Specialization)
            .where(Specialization.is_active == True)
            .order_by(Specialization.display_order.asc(), Specialization.name.asc())
        )
        return list(result.scalars().all())
    
    async def get_all(self) -> List[Specialization]:
        """Get all specializations (including inactive)."""
        result = await self.session.execute(
            select(Specialization)
            .order_by(Specialization.display_order.asc(), Specialization.name.asc())
        )
        return list(result.scalars().all())
    
    async def update(self, specialization: Specialization) -> Specialization:
        """Update specialization."""
        await self.session.commit()
        await self.session.refresh(specialization)
        return specialization
    
    async def delete(self, specialization: Specialization):
        """Delete specialization."""
        await self.session.delete(specialization)
        await self.session.commit()
    
    async def deactivate(self, specialization_id: int) -> bool:
        """Deactivate a specialization instead of deleting."""
        result = await self.session.execute(
            update(Specialization)
            .where(Specialization.id == specialization_id)
            .values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def activate(self, specialization_id: int) -> bool:
        """Activate a specialization."""
        result = await self.session.execute(
            update(Specialization)
            .where(Specialization.id == specialization_id)
            .values(is_active=True)
        )
        await self.session.commit()
        return result.rowcount > 0

