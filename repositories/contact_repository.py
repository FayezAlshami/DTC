"""Contact request repository."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from database.models import ContactRequest, ContactRequestStatus


class ContactRequestRepository:
    """Repository for contact request operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, contact_request: ContactRequest) -> ContactRequest:
        """Create a new contact request."""
        self.session.add(contact_request)
        await self.session.commit()
        await self.session.refresh(contact_request)
        return contact_request
    
    async def get_by_id(self, contact_id: int) -> Optional[ContactRequest]:
        """Get contact request by ID."""
        result = await self.session.execute(
            select(ContactRequest)
            .options(
                selectinload(ContactRequest.requester),
                selectinload(ContactRequest.provider),
                selectinload(ContactRequest.service),
                selectinload(ContactRequest.service_request)
            )
            .where(ContactRequest.id == contact_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user(self, user_id: int) -> List[ContactRequest]:
        """Get all contact requests for a user (as requester or provider)."""
        result = await self.session.execute(
            select(ContactRequest)
            .options(
                selectinload(ContactRequest.requester),
                selectinload(ContactRequest.provider),
                selectinload(ContactRequest.service),
                selectinload(ContactRequest.service_request)
            )
            .where(
                or_(
                    ContactRequest.requester_id == user_id,
                    ContactRequest.provider_id == user_id
                )
            )
            .order_by(ContactRequest.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_pending_for_provider(self, provider_id: int) -> List[ContactRequest]:
        """Get pending contact requests for a provider."""
        result = await self.session.execute(
            select(ContactRequest)
            .options(selectinload(ContactRequest.requester))
            .where(
                and_(
                    ContactRequest.provider_id == provider_id,
                    ContactRequest.status == ContactRequestStatus.PENDING
                )
            )
            .order_by(ContactRequest.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def update(self, contact_request: ContactRequest) -> ContactRequest:
        """Update contact request."""
        await self.session.commit()
        await self.session.refresh(contact_request)
        return contact_request

