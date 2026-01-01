"""Service for managing services."""
from typing import Optional
from decimal import Decimal
import decimal
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.service_repository import ServiceRepository
from repositories.user_repository import UserRepository
from services.profile_service import ProfileService
from database.models import Service, ServiceStatus, User
from config import config


class ServiceService:
    """Service for service operations."""
    
    def __init__(self, session: AsyncSession):
        self.service_repo = ServiceRepository(session)
        self.user_repo = UserRepository(session)
        self.profile_service = ProfileService(session)
    
    def validate_price(self, price_str: str) -> tuple[bool, Optional[str], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Validate price format (fixed or range)."""
        if not price_str or not isinstance(price_str, str):
            return False, "يرجى إدخال قيمة صحيحة للسعر.", None, None, None
        
        # تنظيف وتحقق من القيمة
        price_str = price_str.strip().replace("$", "").replace(",", "").replace(" ", "")
        
        # إزالة الأحرف غير الرقمية
        import re
        price_str = re.sub(r'[^\d.\-]', '', price_str)
        
        if not price_str:
            return False, "يرجى إدخال رقم صحيح للسعر (مثال: 150 أو 150-200).", None, None, None
        
        if "-" in price_str:
            # Range
            parts = price_str.split("-")
            if len(parts) != 2:
                return False, "صيغة نطاق السعر غير صحيحة. استخدم: حد أدنى-حد أعلى (مثال: 200-300)", None, None, None
            
            min_part = parts[0].strip()
            max_part = parts[1].strip()
            
            if not min_part or not max_part:
                return False, "يرجى إدخال الحد الأدنى والأعلى للسعر (مثال: 200-300).", None, None, None
            
            try:
                min_price = Decimal(min_part)
                max_price = Decimal(max_part)
                if min_price <= 0 or max_price <= 0:
                    return False, "الأسعار يجب أن تكون أرقاماً موجبة.", None, None, None
                if min_price >= max_price:
                    return False, "السعر الأدنى يجب أن يكون أقل من السعر الأعلى.", None, None, None
                return True, None, None, min_price, max_price
            
            except (ValueError, decimal.InvalidOperation, Exception):
                return False, "صيغة السعر غير صحيحة. استخدم أرقاماً فقط (مثال: 200-300).", None, None, None
        else:
            # Fixed
            try:
                price = Decimal(price_str)
                if price <= 0:
                    return False, "السعر يجب أن يكون رقماً موجباً.", None, None, None
                return True, None, price, None, None
            except (ValueError, decimal.InvalidOperation, Exception):
                return False, "صيغة السعر غير صحيحة. استخدم رقماً فقط (مثال: 150 أو 150$).", None, None, None

    
    async def create_service(
        self,
        provider: User,
        title: str,
        description: str,
        price_str: str,
        media_file_id: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> tuple[bool, Optional[Service], Optional[str]]:
        """Create a new service."""
        # Check if user can provide services
        can_provide, error = self.profile_service.can_provide_service(provider)
        if not can_provide:
            return False, None, error
        
        # Validate title
        if not title or len(title.strip()) < 5:
            return False, None, "Title must be at least 5 characters long."
        if len(title) > config.MAX_TITLE_LENGTH:
            return False, None, f"Title must be no more than {config.MAX_TITLE_LENGTH} characters."
        
        # Validate description
        if not description or len(description.strip()) < 20:
            return False, None, "Description must be at least 20 characters long."
        if not media_file_id and len(description) > config.MAX_DESCRIPTION_LENGTH:
            return False, None, f"Description must be no more than {config.MAX_DESCRIPTION_LENGTH} characters when no media is provided."
        
        # Validate price
        is_valid, error, price_fixed, price_min, price_max = self.validate_price(price_str)
        if not is_valid:
            return False, None, error
        
        # Create service
        provider_id: int = provider.id  # type: ignore[assignment]
        provider_specialization: str = provider.specialization  # type: ignore[assignment]
        service = Service(
            provider_id=provider_id,
            title=title.strip(),
            description=description.strip(),
            price_type="fixed" if price_max is None else "range",
            price_fixed=price_fixed,
            price_min=price_min,
            price_max=price_max,
            specialization=provider_specialization,
            media_file_id=media_file_id,
            media_type=media_type,
            status=ServiceStatus.DRAFT.value  # type: ignore
        )
        
        service = await self.service_repo.create(service)
        return True, service, None
    
    def format_price(self, service: Service) -> str:
        """Format service price for display."""
        price_type = str(service.price_type) if service.price_type else "fixed"  # type: ignore
        
        if price_type == "fixed":
            return f"${service.price_fixed}"
        else:
            return f"${service.price_min} - ${service.price_max}"


