"""Service request repository."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.models import ServiceRequest, RequestStatus


class ServiceRequestRepository:
    """Repository for service request operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, request: ServiceRequest) -> ServiceRequest:
        """Create a new service request."""
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request
    
    async def get_by_id(self, request_id: int) -> Optional[ServiceRequest]:
        """Get request by ID."""
        result = await self.session.execute(
            select(ServiceRequest).options(selectinload(ServiceRequest.requester))
            .where(ServiceRequest.id == request_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_requester(self, requester_id: int, skip: int = 0, limit: int = 100) -> List[ServiceRequest]:
        """Get requests by requester."""
        result = await self.session.execute(
            select(ServiceRequest).where(ServiceRequest.requester_id == requester_id)
            .order_by(ServiceRequest.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_published_requests(self, skip: int = 0, limit: int = 100) -> List[ServiceRequest]:
        """Get published requests."""
        result = await self.session.execute(
            select(ServiceRequest).options(selectinload(ServiceRequest.requester))
            .where(ServiceRequest.status == RequestStatus.PUBLISHED)
            .order_by(ServiceRequest.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def update(self, request: ServiceRequest) -> ServiceRequest:
        """Update request."""
        await self.session.commit()
        await self.session.refresh(request)
        return request
    
    async def delete(self, request: ServiceRequest):
        """Delete request."""
        await self.session.delete(request)
        await self.session.commit()
    
    async def get_all_requests(self, skip: int = 0, limit: int = 100) -> List[ServiceRequest]:
        """Get all requests (for admin)."""
        result = await self.session.execute(
            select(ServiceRequest).options(selectinload(ServiceRequest.requester))
            .order_by(ServiceRequest.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

