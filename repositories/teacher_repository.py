"""Teacher repository."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from database.models import User, UserRole, TeacherSpecialization, TeacherSubject, Subject, Specialization


class TeacherRepository:
    """Repository for teacher operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all_teachers(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with TEACHER role."""
        result = await self.session.execute(
            select(User)
            .where(User.role == UserRole.TEACHER)
            .options(
                selectinload(User.teacher_specializations).selectinload(TeacherSpecialization.specialization),
                selectinload(User.teacher_subjects).selectinload(TeacherSubject.subject)
            )
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_teacher_by_id(self, teacher_id: int) -> Optional[User]:
        """Get teacher by ID with specializations and subjects."""
        result = await self.session.execute(
            select(User)
            .where(User.id == teacher_id, User.role == UserRole.TEACHER)
            .options(
                selectinload(User.teacher_specializations).selectinload(TeacherSpecialization.specialization),
                selectinload(User.teacher_subjects).selectinload(TeacherSubject.subject)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_teachers_by_specialization(self, specialization_id: int) -> List[User]:
        """Get all teachers for a specific specialization."""
        result = await self.session.execute(
            select(User)
            .join(TeacherSpecialization)
            .where(
                TeacherSpecialization.specialization_id == specialization_id,
                User.role == UserRole.TEACHER
            )
            .options(
                selectinload(User.teacher_specializations).selectinload(TeacherSpecialization.specialization),
                selectinload(User.teacher_subjects).selectinload(TeacherSubject.subject)
            )
        )
        return list(result.scalars().all())
    
    async def get_teachers_by_subject(self, subject_id: int) -> List[User]:
        """Get all teachers for a specific subject."""
        result = await self.session.execute(
            select(User)
            .join(TeacherSubject)
            .where(
                TeacherSubject.subject_id == subject_id,
                TeacherSubject.is_active == True,
                User.role == UserRole.TEACHER
            )
            .options(
                selectinload(User.teacher_specializations).selectinload(TeacherSpecialization.specialization),
                selectinload(User.teacher_subjects).selectinload(TeacherSubject.subject)
            )
        )
        return list(result.scalars().all())
    
    # Teacher Specialization methods
    async def add_specialization(self, teacher_id: int, specialization_id: int, is_primary: bool = False) -> TeacherSpecialization:
        """Add a specialization to a teacher."""
        # Check if already exists
        existing = await self.get_teacher_specialization(teacher_id, specialization_id)
        if existing:
            return existing
        
        teacher_spec = TeacherSpecialization(
            teacher_id=teacher_id,
            specialization_id=specialization_id,
            is_primary=is_primary
        )
        self.session.add(teacher_spec)
        await self.session.commit()
        await self.session.refresh(teacher_spec)
        return teacher_spec
    
    async def remove_specialization(self, teacher_id: int, specialization_id: int) -> bool:
        """Remove a specialization from a teacher."""
        result = await self.session.execute(
            delete(TeacherSpecialization).where(
                TeacherSpecialization.teacher_id == teacher_id,
                TeacherSpecialization.specialization_id == specialization_id
            )
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_teacher_specialization(self, teacher_id: int, specialization_id: int) -> Optional[TeacherSpecialization]:
        """Get a specific teacher-specialization relationship."""
        result = await self.session.execute(
            select(TeacherSpecialization).where(
                TeacherSpecialization.teacher_id == teacher_id,
                TeacherSpecialization.specialization_id == specialization_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_teacher_specializations(self, teacher_id: int) -> List[TeacherSpecialization]:
        """Get all specializations for a teacher."""
        result = await self.session.execute(
            select(TeacherSpecialization)
            .where(TeacherSpecialization.teacher_id == teacher_id)
            .options(selectinload(TeacherSpecialization.specialization))
        )
        return list(result.scalars().all())
    
    async def set_primary_specialization(self, teacher_id: int, specialization_id: int) -> bool:
        """Set a specialization as primary for a teacher."""
        # First, unset all primary flags for this teacher
        await self.session.execute(
            select(TeacherSpecialization)
            .where(TeacherSpecialization.teacher_id == teacher_id)
        )
        
        # Update all to not primary
        from sqlalchemy import update
        await self.session.execute(
            update(TeacherSpecialization)
            .where(TeacherSpecialization.teacher_id == teacher_id)
            .values(is_primary=False)
        )
        
        # Set the specified one as primary
        await self.session.execute(
            update(TeacherSpecialization)
            .where(
                TeacherSpecialization.teacher_id == teacher_id,
                TeacherSpecialization.specialization_id == specialization_id
            )
            .values(is_primary=True)
        )
        await self.session.commit()
        return True
    
    # Teacher Subject methods
    async def add_subject(
        self, 
        teacher_id: int, 
        subject_id: int, 
        academic_year: Optional[str] = None,
        semester: Optional[str] = None
    ) -> TeacherSubject:
        """Add a subject to a teacher."""
        teacher_subject = TeacherSubject(
            teacher_id=teacher_id,
            subject_id=subject_id,
            academic_year=academic_year,
            semester=semester,
            is_active=True
        )
        self.session.add(teacher_subject)
        await self.session.commit()
        await self.session.refresh(teacher_subject)
        return teacher_subject
    
    async def remove_subject(self, teacher_id: int, subject_id: int) -> bool:
        """Remove a subject from a teacher."""
        result = await self.session.execute(
            delete(TeacherSubject).where(
                TeacherSubject.teacher_id == teacher_id,
                TeacherSubject.subject_id == subject_id
            )
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_teacher_subjects(self, teacher_id: int, active_only: bool = True) -> List[TeacherSubject]:
        """Get all subjects for a teacher."""
        query = select(TeacherSubject).where(TeacherSubject.teacher_id == teacher_id)
        if active_only:
            query = query.where(TeacherSubject.is_active == True)
        query = query.options(selectinload(TeacherSubject.subject))
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def deactivate_teacher_subject(self, teacher_id: int, subject_id: int) -> bool:
        """Deactivate a teacher-subject relationship."""
        from sqlalchemy import update
        result = await self.session.execute(
            update(TeacherSubject)
            .where(
                TeacherSubject.teacher_id == teacher_id,
                TeacherSubject.subject_id == subject_id
            )
            .values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0

