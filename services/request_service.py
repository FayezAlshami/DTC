"""Service for managing service requests."""
from typing import List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.request_repository import ServiceRequestRepository
from database.models import ServiceRequest, RequestStatus, User, Gender
from config import config


class RequestService:
    """Service for request operations."""
    
    def __init__(self, session: AsyncSession):
        self.request_repo = ServiceRequestRepository(session)
    
    def validate_budget(self, budget_str: str) -> tuple[bool, Optional[str], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Validate budget format (fixed or range)."""
        if not budget_str or not isinstance(budget_str, str):
            return False, "يرجى إدخال قيمة صحيحة للميزانية.", None, None, None
        
        budget_str = budget_str.strip().replace("$", "").replace(",", "").replace(" ", "")
        
        import re
        budget_str = re.sub(r'[^\d.\-]', '', budget_str)
        
        if not budget_str:
            return False, "يرجى إدخال رقم صحيح للميزانية (مثال: 150 أو 150-200).", None, None, None
        
        if "-" in budget_str:
            parts = budget_str.split("-")
            if len(parts) != 2:
                return False, "صيغة الميزانية غير صحيحة. استخدم: حد أدنى-حد أعلى (مثال: 200-300)", None, None, None
            
            min_part = parts[0].strip()
            max_part = parts[1].strip()
            
            if not min_part or not max_part:
                return False, "يرجى إدخال الحد الأدنى والأعلى للميزانية (مثال: 200-300).", None, None, None
            
            try:
                min_budget = Decimal(min_part)
                max_budget = Decimal(max_part)
                
                if min_budget <= 0 or max_budget <= 0:
                    return False, "يجب أن تكون الميزانية أرقاماً موجبة.", None, None, None
                if min_budget >= max_budget:
                    return False, "الحد الأدنى يجب أن يكون أقل من الحد الأعلى.", None, None, None
                return True, None, None, min_budget, max_budget
            except (ValueError, Exception):
                return False, "صيغة الميزانية غير صحيحة. استخدم أرقاماً فقط (مثال: 200-300).", None, None, None
        else:
            try:
                budget = Decimal(budget_str)
                if budget <= 0:
                    return False, "يجب أن تكون الميزانية رقماً موجباً.", None, None, None
                return True, None, budget, None, None
            except (ValueError, Exception):
                return False, "صيغة الميزانية غير صحيحة. استخدم رقماً فقط (مثال: 150 أو 150$).", None, None, None
    
    async def create_request(
        self,
        requester: User,
        title: str,
        description: str,
        allowed_specializations: List[str],
        budget_str: str,
        preferred_gender: Optional[Gender] = None
    ) -> tuple[bool, Optional[ServiceRequest], Optional[str]]:
        """Create a new service request."""
        if not title or len(title.strip()) < 5:
            return False, None, "Title must be at least 5 characters long."
        if len(title) > config.MAX_TITLE_LENGTH:
            return False, None, f"Title must be no more than {config.MAX_TITLE_LENGTH} characters."
        
        if not description or len(description.strip()) < 20:
            return False, None, "Description must be at least 20 characters long."
        if len(description) > config.MAX_DESCRIPTION_LENGTH:
            return False, None, f"Description must be no more than {config.MAX_DESCRIPTION_LENGTH} characters."
        
        if not allowed_specializations or len(allowed_specializations) == 0:
            return False, None, "At least one specialization must be specified."
        
        is_valid, error, budget_fixed, budget_min, budget_max = self.validate_budget(budget_str)
        if not is_valid:
            return False, None, error
        
        requester_id: int = requester.id  # type: ignore[assignment]
        request = ServiceRequest(
            requester_id=requester_id,
            title=title.strip(),
            description=description.strip(),
            allowed_specializations=allowed_specializations,
            budget_type="fixed" if budget_max is None else "range",
            budget_fixed=budget_fixed,
            budget_min=budget_min,
            budget_max=budget_max,
            preferred_gender=preferred_gender,
            status=RequestStatus.DRAFT.value  # type: ignore
        )
        
        request = await self.request_repo.create(request)
        return True, request, None
    
    def format_budget(self, request: ServiceRequest) -> str:
        """Format request budget for display."""
        if request.budget_type == "fixed":  # type: ignore[truthy-bool]
            return f"${request.budget_fixed}"
        else:
            return f"${request.budget_min} - ${request.budget_max}"
    
    def can_respond_to_request(self, user: User, request: ServiceRequest) -> tuple[bool, Optional[str]]:
        """Check if user can respond to a request."""
        if not user.is_student:  # type: ignore[truthy-bool]
            return False, "فقط الطلاب يمكنهم تقديم الخدمات للطلبات."
        
        if not user.profile_completed:  # type: ignore[truthy-bool]
            return False, "يجب إكمال ملفك الشخصي أولاً."
        
        user_specialization = getattr(user, 'specialization', None)
        if not user_specialization:
            return False, "يجب أن يكون لديك تخصص محدد لتقديم الخدمات."
        
        allowed_specs = request.allowed_specializations if isinstance(request.allowed_specializations, list) else []
        if user_specialization not in allowed_specs:
            return False, f"تخصصك ({user_specialization}) غير مسموح به لهذا الطلب. التخصصات المطلوبة: {', '.join(allowed_specs)}"
        
        if request.preferred_gender:  # type: ignore[truthy-value]
            user_gender = getattr(user, 'gender', None)
            if user_gender and request.preferred_gender != user_gender:  # type: ignore[truthy-bool]
                gender_names = {"male": "ذكر", "female": "أنثى"}
                preferred = gender_names.get(str(request.preferred_gender), str(request.preferred_gender))
                return False, f"هذا الطلب يتطلب جنس: {preferred}"
        
        return True, None
