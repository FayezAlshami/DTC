"""Profile service."""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repository import UserRepository
from database.models import User, UserRole, Gender


class ProfileService:
    """Service for profile operations."""
    
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format."""
        # Basic validation - can be enhanced
        phone = phone.replace(" ", "").replace("-", "").replace("+", "")
        return phone.isdigit() and len(phone) >= 10
    
    async def update_profile(
        self,
        user: User,
        full_name: Optional[str] = None,
        student_id: Optional[str] = None,
        specialization: Optional[str] = None,
        phone_number: Optional[str] = None,
        date_of_birth: Optional[datetime] = None,
        gender: Optional[Gender] = None
    ) -> tuple[bool, Optional[str]]:
        """Update user profile."""
        if full_name:
            if len(full_name) < 2 or len(full_name) > 255:
                return False, "Full name must be between 2 and 255 characters."
            user.full_name = full_name
        
        if student_id:
            if len(student_id) < 3 or len(student_id) > 100:
                return False, "Student ID must be between 3 and 100 characters."
            user.student_id = student_id
        
        if specialization:
            if len(specialization) < 2 or len(specialization) > 255:
                return False, "Specialization must be between 2 and 255 characters."
            user.specialization = specialization
        
        if phone_number:
            if not self.validate_phone(phone_number):
                return False, "Invalid phone number format."
            user.phone_number = phone_number
        
        if date_of_birth:
            if date_of_birth > datetime.now():
                return False, "Date of birth cannot be in the future."
            user.date_of_birth = date_of_birth
        
        if gender:
            user.gender = gender
        
        # Check if profile is complete
        user.profile_completed = self.is_profile_complete(user)
        
        # If user has student_id and specialization, mark as student
        if user.student_id and user.specialization:
            user.is_student = True
        
        await self.user_repo.update(user)
        return True, None
    
    def is_profile_complete(self, user: User) -> bool:
        """Check if user profile is complete."""
        required_fields = [user.full_name]
        
        # If user wants to provide services, student fields are required
        if user.is_student or (user.student_id and user.specialization):
            required_fields.extend([user.student_id, user.specialization])
        
        return all(field is not None and str(field).strip() for field in required_fields)
    
    def can_provide_service(self, user: User) -> tuple[bool, Optional[str]]:
        """Check if user can provide services."""
        if not user.is_student:
            return False, "You must be a student to provide services."
        
        if not self.is_profile_complete(user):
            return False, "You must complete your profile to provide services."
        
        if not user.student_id or not user.specialization:
            return False, "Student ID and specialization are required to provide services."
        
        return True, None

