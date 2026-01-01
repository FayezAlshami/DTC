"""Service repository."""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from database.models import Service, ServiceStatus, User


class ServiceRepository:
    """Repository for service operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, service: Service) -> Service:
        """Create a new service."""
        self.session.add(service)
        await self.session.commit()
        await self.session.refresh(service)
        return service
    
    async def get_by_id(self, service_id: int) -> Optional[Service]:
        """Get service by ID."""
        result = await self.session.execute(
            select(Service).options(selectinload(Service.provider)).where(Service.id == service_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_provider(self, provider_id: int, skip: int = 0, limit: int = 100) -> List[Service]:
        """Get services by provider."""
        result = await self.session.execute(
            select(Service).where(Service.provider_id == provider_id)
            .order_by(Service.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_published_services(
        self, 
        specialization: Optional[str] = None,
        max_price: Optional[Decimal] = None,
        min_price: Optional[Decimal] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[Service]:
        """Get published services with filters."""
        query = select(Service).options(selectinload(Service.provider)).where(
            Service.status == ServiceStatus.PUBLISHED
        )
        
        if specialization:
            query = query.where(Service.specialization == specialization)
        
        if min_price is not None or max_price is not None:
            conditions = []
            if min_price is not None:
                conditions.append(
                    or_(
                        Service.price_fixed >= min_price,
                        Service.price_max >= min_price
                    )
                )
            if max_price is not None:
                conditions.append(
                    or_(
                        Service.price_fixed <= max_price,
                        Service.price_min <= max_price
                    )
                )
            if conditions:
                query = query.where(and_(*conditions))
        
        result = await self.session.execute(
            query.order_by(Service.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def update(self, service: Service) -> Service:
        """Update service."""
        await self.session.commit()
        await self.session.refresh(service)
        return service
    
    async def delete(self, service: Service):
        """Delete service."""
        await self.session.delete(service)
        await self.session.commit()
    
    async def get_all_services(self, skip: int = 0, limit: int = 100) -> List[Service]:
        """Get all services (for admin)."""
        result = await self.session.execute(
            select(Service).options(selectinload(Service.provider))
            .order_by(Service.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

