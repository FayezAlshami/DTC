"""Database models."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    ForeignKey, Numeric, Enum as SQLEnum, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.base import Base


class UserRole(PyEnum):
    """User role enumeration (stored uppercase to match DB)."""
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    VISITOR = "VISITOR"
    USER = "USER"


class Gender(PyEnum):
    """Gender enumeration."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ServiceStatus(PyEnum):
    """Service status enumeration."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"  # Waiting for admin approval
    PUBLISHED = "PUBLISHED"
    REMOVED = "REMOVED"
    COMPLETED = "COMPLETED"
    CONTACT_ACCEPTED = "CONTACT_ACCEPTED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"  # Rejected by admin


class RequestStatus(PyEnum):
    """Service request status enumeration."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    REMOVED = "REMOVED"
    COMPLETED = "COMPLETED"
    CONTACT_ACCEPTED = "CONTACT_ACCEPTED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class ContactRequestStatus(PyEnum):
    """Contact request status enumeration."""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_student = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Profile fields
    full_name = Column(String(255), nullable=True)
    student_id = Column(String(100), nullable=True)  # رقم الطالب
    teacher_number = Column(String(100), nullable=True)  # رقم الأستاذ
    visitor_number = Column(String(100), nullable=True)  # رقم الزائر
    specialization = Column(String(255), nullable=True)
    specialization_id = Column(Integer, ForeignKey("specializations.id"), nullable=True)  # FK للاختصاص
    phone_number = Column(String(50), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(SQLEnum(Gender), nullable=True)

    # Profile completion
    profile_completed = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    services = relationship("Service", back_populates="provider", cascade="all, delete-orphan")
    service_requests = relationship("ServiceRequest", back_populates="requester", cascade="all, delete-orphan")
    contact_requests_sent = relationship("ContactRequest", foreign_keys="ContactRequest.requester_id", back_populates="requester")
    contact_requests_received = relationship("ContactRequest", foreign_keys="ContactRequest.provider_id", back_populates="provider")
    verification_codes = relationship("VerificationCode", back_populates="user", cascade="all, delete-orphan")
    admin_logs = relationship("AdminLog", back_populates="admin")
    contact_accounts = relationship("ContactAccount", back_populates="user", cascade="all, delete-orphan")
    
    # Teacher relationships (for users with TEACHER role)
    teacher_specializations = relationship("TeacherSpecialization", back_populates="teacher", cascade="all, delete-orphan")
    teacher_subjects = relationship("TeacherSubject", back_populates="teacher", cascade="all, delete-orphan")


class VerificationCode(Base):
    """Email verification code model."""
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="verification_codes")


class Service(Base):
    """Service model (provided by students)."""
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    price_type = Column(String(20), nullable=False)  # "fixed" or "range"
    price_fixed = Column(Numeric(10, 2), nullable=True)
    price_min = Column(Numeric(10, 2), nullable=True)
    price_max = Column(Numeric(10, 2), nullable=True)
    specialization = Column(String(255), nullable=False)
    media_file_id = Column(String(255), nullable=True)  # Telegram file ID
    media_type = Column(String(20), nullable=True)  # "photo" or "video"
    status = Column(SQLEnum(ServiceStatus), default=ServiceStatus.DRAFT, nullable=False)
    channel_message_id = Column(Integer, nullable=True)  # Message ID in Telegram channel
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    provider = relationship("User", back_populates="services")
    contact_requests = relationship("ContactRequest", back_populates="service")


class ServiceRequest(Base):
    """Service request model (requested by users)."""
    __tablename__ = "service_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    allowed_specializations = Column(JSON, nullable=False)  # List of specializations
    budget_type = Column(String(20), nullable=False)  # "fixed" or "range"
    budget_fixed = Column(Numeric(10, 2), nullable=True)
    budget_min = Column(Numeric(10, 2), nullable=True)
    budget_max = Column(Numeric(10, 2), nullable=True)
    preferred_gender = Column(SQLEnum(Gender), nullable=True)  # Preferred gender for service provider
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.DRAFT, nullable=False)
    channel_message_id = Column(Integer, nullable=True)  # Message ID in Telegram channel
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    requester = relationship("User", back_populates="service_requests")
    contact_requests = relationship("ContactRequest", back_populates="service_request")


class ContactRequest(Base):
    """Contact request model."""
    __tablename__ = "contact_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    status = Column(SQLEnum(ContactRequestStatus), default=ContactRequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id], back_populates="contact_requests_sent")
    provider = relationship("User", foreign_keys=[provider_id], back_populates="contact_requests_received")
    service = relationship("Service", back_populates="contact_requests")
    service_request = relationship("ServiceRequest", back_populates="contact_requests")


class AdminLog(Base):
    """Admin action log model."""
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)  # "user", "service", "request", etc.
    target_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    admin = relationship("User", back_populates="admin_logs")


class Specialization(Base):
    """Specialization model for managing available specializations."""
    __tablename__ = "specializations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)  # For ordering in UI
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    subjects = relationship("Subject", back_populates="specialization", cascade="all, delete-orphan")
    teachers = relationship("TeacherSpecialization", back_populates="specialization", cascade="all, delete-orphan")


class ContactAccount(Base):
    """Contact account model for user social media accounts."""
    __tablename__ = "contact_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # facebook, telegram, whatsapp, etc.
    username = Column(String(255), nullable=True)  # username or handle
    url = Column(String(500), nullable=True)  # full URL if available
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="contact_accounts")


class Subject(Base):
    """Subject/Course model - مادة دراسية مرتبطة باختصاص."""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), nullable=True, unique=True)  # رمز المادة (اختياري)
    description = Column(Text, nullable=True)
    specialization_id = Column(Integer, ForeignKey("specializations.id"), nullable=False, index=True)
    credit_hours = Column(Integer, nullable=True)  # الساعات المعتمدة
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    specialization = relationship("Specialization", back_populates="subjects")
    teachers = relationship("TeacherSubject", back_populates="subject", cascade="all, delete-orphan")


class TeacherSpecialization(Base):
    """Many-to-many relationship between teachers and specializations - ربط الأستاذ بالاختصاصات."""
    __tablename__ = "teacher_specializations"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    specialization_id = Column(Integer, ForeignKey("specializations.id"), nullable=False, index=True)
    is_primary = Column(Boolean, default=False, nullable=False)  # هل هو الاختصاص الرئيسي
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    teacher = relationship("User", back_populates="teacher_specializations")
    specialization = relationship("Specialization", back_populates="teachers")


class TeacherSubject(Base):
    """Many-to-many relationship between teachers and subjects - ربط الأستاذ بالمواد التي يدرسها."""
    __tablename__ = "teacher_subjects"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    academic_year = Column(String(20), nullable=True)  # السنة الدراسية (مثال: 2024-2025)
    semester = Column(String(20), nullable=True)  # الفصل الدراسي
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    teacher = relationship("User", back_populates="teacher_subjects")
    subject = relationship("Subject", back_populates="teachers")