"""Admin repository."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import AdminLog, User, Service, ServiceRequest, ContactRequest, ContactRequestStatus


class AdminRepository:
    """Repository for admin operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_action(
        self, 
        admin_id: int, 
        action_type: str, 
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        details: Optional[dict] = None
    ):
        """Log an admin action."""
        log = AdminLog(
            admin_id=admin_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            details=details
        )
        self.session.add(log)
        await self.session.commit()
    
    async def get_statistics(self) -> dict:
        """Get platform statistics."""
        total_users = await self.session.scalar(select(func.count(User.id)))
        active_users = await self.session.scalar(
            select(func.count(User.id)).where(User.is_active == True)
        )
        student_users = await self.session.scalar(
            select(func.count(User.id)).where(User.is_student == True)
        )
        total_services = await self.session.scalar(select(func.count(Service.id)))
        total_requests = await self.session.scalar(select(func.count(ServiceRequest.id)))
        completed_contacts = await self.session.scalar(
            select(func.count(ContactRequest.id)).where(
                ContactRequest.status == ContactRequestStatus.ACCEPTED
            )
        )
        
        return {
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "student_users": student_users or 0,
            "total_services": total_services or 0,
            "total_requests": total_requests or 0,
            "completed_contacts": completed_contacts or 0
        }

