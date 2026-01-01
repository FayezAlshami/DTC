"""Common utilities and middleware."""

from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from database.base import AsyncSessionLocal
from repositories.user_repository import UserRepository
from database.models import User, UserRole
from functools import wraps


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["db_session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Middleware to load user from database."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        session: AsyncSession = data["db_session"]
        tg_user: Optional[TgUser] = data.get("event_from_user")

        if tg_user:
            user_repo = UserRepository(session)
            user: Optional[User] = await user_repo.get_by_telegram_id(tg_user.id)
            data["user"] = user

        return await handler(event, data)


def require_auth(handler):
    """Decorator to require authentication and email verification."""
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        user: Optional[User] = kwargs.get("user")
        
        if user is None:
            # جلب الـ message من args
            message = args[0] if args and isinstance(args[0], (Message, CallbackQuery)) else kwargs.get("message")
            callback = args[0] if args and isinstance(args[0], CallbackQuery) else kwargs.get("callback")
            
            if callback:
                await callback.answer("يجب تسجيل الدخول أولاً", show_alert=True)
                return
            elif message:
                await message.answer("❌ يجب تسجيل الدخول أولاً.\n\nيرجى استخدام /start لتسجيل الدخول أو إنشاء حساب جديد.")
            return
        
        # Check if email is verified
        email_verified: bool = user.email_verified  # type: ignore[assignment]
        if not email_verified:
            message = args[0] if args and isinstance(args[0], (Message, CallbackQuery)) else kwargs.get("message")
            callback = args[0] if args and isinstance(args[0], CallbackQuery) else kwargs.get("callback")
            
            if callback:
                await callback.answer("⚠️ يجب التحقق من بريدك الإلكتروني أولاً. استخدم /start للتحقق.", show_alert=True)
                return
            elif message:
                await message.answer(
                    "⚠️ يجب التحقق من بريدك الإلكتروني قبل استخدام هذه الميزة.\n\n"
                    "يرجى استخدام /start للتحقق من بريدك الإلكتروني."
                )
            return
        
        # مرر الـ kwargs كما هي بدون تعديل (user موجودة أصلاً ومتحقق منها)
        return await handler(*args, **kwargs)
    
    return wrapper


def require_student(handler):
    """Decorator to require student role."""
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        user: Optional[User] = kwargs.get("user")
        
        if user is None or user.role != UserRole.STUDENT:
            message = args[0] if args and isinstance(args[0], (Message, CallbackQuery)) else kwargs.get("message")
            callback = args[0] if args and isinstance(args[0], CallbackQuery) else kwargs.get("callback")
            
            if callback:
                await callback.answer("هذه الميزة متاحة للطلاب فقط.", show_alert=True)
                return
            elif message:
                await message.answer("❌ هذه الميزة متاحة للطلاب فقط.")
            return
        
        return await handler(*args, **kwargs)
    
    return wrapper


def require_admin(handler):
    """Decorator to require admin role."""
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        user: Optional[User] = kwargs.get("user")
        
        if user is None or user.role != UserRole.ADMIN:
            message = args[0] if args and isinstance(args[0], (Message, CallbackQuery)) else kwargs.get("message")
            if message:
                await message.answer("هذه الميزة متاحة للمديرين فقط.")
            return
        
        return await handler(*args, **kwargs)
    
    return wrapper


def require_teacher(handler):
    """Decorator to require teacher role."""
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        user: Optional[User] = kwargs.get("user")
        
        if user is None or user.role != UserRole.TEACHER:
            message = args[0] if args and isinstance(args[0], (Message, CallbackQuery)) else kwargs.get("message")
            callback = args[0] if args and isinstance(args[0], CallbackQuery) else kwargs.get("callback")
            
            if callback:
                await callback.answer("هذه الميزة متاحة للأساتذة فقط.", show_alert=True)
                return
            elif message:
                await message.answer("❌ هذه الميزة متاحة للأساتذة فقط.")
            return
        
        return await handler(*args, **kwargs)
    
    return wrapper
