"""Start command handler."""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import get_start_keyboard, get_main_menu_keyboard, get_verification_retry_keyboard
from handlers.common import require_auth
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repository import UserRepository
from database.models import User

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_verification_code = State()


class LoginStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext, db_session: AsyncSession, user: User = None):
    """Handle /start command."""
    if user:
        # Check if email is verified
        email_verified: bool = user.email_verified  # type: ignore[assignment]
        if not email_verified:
            # User exists but email not verified - show verification message
            data = await state.get_data()
            user_id: int = user.id  # type: ignore[assignment]
            data["user_id"] = user_id
            await state.update_data(data)
            
            await message.answer(
                "⚠️ يجب التحقق من بريدك الإلكتروني قبل استخدام البوت.\n\n"
                "يرجى إدخال رمز التحقق المكون من 6 أرقام الذي تم إرساله إلى بريدك الإلكتروني.\n\n"
                "إذا لم تستلم الرمز، يمكنك استخدام زر 'إعادة إرسال' أدناه.",
                reply_markup=get_verification_retry_keyboard()
            )
            await state.set_state(RegistrationStates.waiting_for_verification_code)
            return
        
        # User is already logged in and verified
        await message.answer(
            "مرحباً بعودتك! اختر خياراً من القائمة:",
            reply_markup=get_main_menu_keyboard(user.profile_completed)
        )
        await state.clear()
    else:
        # Show welcome and login/register options
        await message.answer(
            "مرحباً بك في بوت DTC Job!\n\n"
            "يربط هذا البوت الطلاب الذين يريدون تقديم الخدمات مع المستخدمين الذين يريدون طلب الخدمات.\n\n"
            "يرجى اختيار خيار:",
            reply_markup=get_start_keyboard()
        )
        await state.clear()


@router.message(F.text == "إنشاء حساب جديد")
async def start_registration(message: Message, state: FSMContext):
    """Start registration process."""
    await message.answer(
        "دعنا ننشئ حسابك!\n\n"
        "يرجى إدخال عنوان بريدك الإلكتروني:",
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_email)


@router.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process email input."""
    email = message.text.strip()
    
    from services.auth_service import AuthService
    auth_service = AuthService(db_session)
    
    is_valid, error = await auth_service.validate_email(email)
    if not is_valid:
        await message.answer(f"صيغة البريد الإلكتروني غير صحيحة. {error}\n\nيرجى إدخال عنوان بريد إلكتروني صحيح:")
        return
    
    # Check if email is taken
    from repositories.user_repository import UserRepository
    user_repo = UserRepository(db_session)
    existing_user = await user_repo.get_by_email(email)
    
    if existing_user:
        # Check if the email belongs to the same telegram user and is not verified
        current_telegram_id = message.from_user.id
        existing_telegram_id: int = existing_user.telegram_id  # type: ignore[assignment]
        email_verified: bool = existing_user.email_verified  # type: ignore[assignment]
        
        if existing_telegram_id == current_telegram_id and not email_verified:
            # Same user, unverified email - delete the old user to allow re-registration
            await user_repo.delete(existing_user)
        else:
            # Email belongs to different user or is verified - show error
            await message.answer("أعد المحاولة من جديد هذا البريد الإلكتروني مسجل بالفعل. يرجى استخدام 'تسجيل الدخول' بدلاً من ذلك أو استخدام بريد إلكتروني مختلف.")
            await state.clear()
            return
    
    await state.update_data(email=email)
    await message.answer("الآن يرجى إدخال كلمة مرور (6 أحرف على الأقل):")
    await state.set_state(RegistrationStates.waiting_for_password)


@router.message(RegistrationStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process password input."""
    password = message.text
    
    if len(password) < 6:
        await message.answer("يجب أن تكون كلمة المرور 6 أحرف على الأقل. يرجى المحاولة مرة أخرى:")
        return
    
    email = (await state.get_data())["email"]
    
    from services.auth_service import AuthService
    auth_service = AuthService(db_session)
    
    success, user, error = await auth_service.register_user(message.from_user.id, email, password)
    
    if not success:
        await message.answer(f"فشل التسجيل: {error}\n\nيرجى المحاولة مرة أخرى باستخدام /start")
        await state.clear()
        return
    
    user_id: int = user.id  # type: ignore[assignment]
    await state.update_data(user_id=user_id)
    await message.answer(
        f"تم إرسال رمز التحقق إلى {email}\n\n"
        "يرجى إدخال الرمز المكون من 6 أرقام الذي استلمته:"
    )
    await state.set_state(RegistrationStates.waiting_for_verification_code)


@router.message(RegistrationStates.waiting_for_verification_code)
async def process_verification_code(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process verification code."""
    # Handle button clicks first
    if message.text == "إعادة إرسال":
        # Delegate to resend_code handler
        data = await state.get_data()
        user_id = data.get("user_id")
        
        if not user_id:
            await message.answer("لا توجد جلسة تسجيل نشطة. يرجى البدء من جديد باستخدام /start")
            await state.clear()
            return
        
        from services.auth_service import AuthService
        auth_service = AuthService(db_session)
        
        success, error = await auth_service.resend_code(user_id)
        
        if success:
            await message.answer("تم إرسال رمز تحقق جديد إلى بريدك الإلكتروني. يرجى إدخاله:")
        else:
            await message.answer(
                f"فشل إعادة إرسال الرمز: {error}",
                reply_markup=get_verification_retry_keyboard()
            )
        return
    
    if message.text == "إعادة إدخال عنوان البريد الإلكتروني":
        # Clear user_id and email from state to start fresh
        data = await state.get_data()
        new_data = {k: v for k, v in data.items() if k not in ["user_id", "email"]}
        await state.set_data(new_data)
        
        await message.answer(
            "يرجى إدخال عنوان بريدك الإلكتروني من جديد:",
            reply_markup=None
        )
        await state.set_state(RegistrationStates.waiting_for_email)
        return
    
    code = message.text.strip()
    
    if not code.isdigit() or len(code) != 6:
        await message.answer(
            "صيغة الرمز غير صحيحة. يرجى إدخال الرمز المكون من 6 أرقام:",
            reply_markup=get_verification_retry_keyboard()
        )
        return
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await message.answer("انتهت الجلسة. يرجى البدء من جديد باستخدام /start")
        await state.clear()
        return
    
    from services.auth_service import AuthService
    auth_service = AuthService(db_session)
    
    is_valid = await auth_service.verify_code(user_id, code)
    
    if not is_valid:
        await message.answer(
            "الرمز غير صحيح أو منتهي الصلاحية.",
            reply_markup=get_verification_retry_keyboard()
        )
        return
    
    # Registration successful
    from repositories.user_repository import UserRepository
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_id(user_id)
    
    await message.answer(
        "✅ تم التسجيل بنجاح! أنت الآن مسجل الدخول.\n\n"
        "مرحباً بك في بوت DTC Job!",
        reply_markup=get_main_menu_keyboard(user.profile_completed)
    )
    await state.clear()


@router.message((F.text.lower() == "resend") | (F.text == "إعادة إرسال"))
async def resend_code(message: Message, state: FSMContext, db_session: AsyncSession):
    """Resend verification code (handles messages outside verification state)."""
    current_state = await state.get_state()
    
    # If we're in verification state, process_verification_code will handle it
    # This handler is only for edge cases outside the normal flow
    if current_state == RegistrationStates.waiting_for_verification_code:
        return
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await message.answer("لا توجد جلسة تسجيل نشطة. يرجى البدء من جديد باستخدام /start")
        await state.clear()
        return
    
    from services.auth_service import AuthService
    auth_service = AuthService(db_session)
    
    success, error = await auth_service.resend_code(user_id)
    
    if success:
        await message.answer("تم إرسال رمز تحقق جديد إلى بريدك الإلكتروني. يرجى إدخاله:")
        await state.set_state(RegistrationStates.waiting_for_verification_code)
    else:
        await message.answer(
            f"فشل إعادة إرسال الرمز: {error}",
            reply_markup=get_verification_retry_keyboard()
        )


@router.message((F.text.lower() == "restart") | (F.text == "إعادة"))
async def restart_registration(message: Message, state: FSMContext):
    """Restart registration (kept for backward compatibility)."""
    await state.clear()
    await message.answer("تم إلغاء التسجيل. استخدم /start للبدء من جديد.")


@router.message(F.text == "تسجيل الدخول")
async def start_login(message: Message, state: FSMContext):
    """Start login process."""
    await message.answer("يرجى إدخال عنوان بريدك الإلكتروني:")
    await state.set_state(LoginStates.waiting_for_email)


@router.message(LoginStates.waiting_for_email)
async def process_login_email(message: Message, state: FSMContext):
    """Process login email."""
    email = message.text.strip()
    await state.update_data(email=email)
    await message.answer("الآن يرجى إدخال كلمة المرور:")
    await state.set_state(LoginStates.waiting_for_password)


@router.message(LoginStates.waiting_for_password)
async def process_login_password(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process login password."""
    password = message.text
    data = await state.get_data()
    email = data["email"]
    
    from services.auth_service import AuthService
    auth_service = AuthService(db_session)
    
    success, user, error = await auth_service.login(email, password)
    
    if not success:
        await message.answer(f"فشل تسجيل الدخول: {error}\n\nيرجى المحاولة مرة أخرى باستخدام /start")
        await state.clear()
        return
    
    # Check if email is verified
    email_verified: bool = user.email_verified  # type: ignore[assignment]
    if not email_verified:
        # User logged in but email not verified - show verification message
        user_id: int = user.id  # type: ignore[assignment]
        data["user_id"] = user_id
        await state.update_data(data)
        
        await message.answer(
            "⚠️ يجب التحقق من بريدك الإلكتروني قبل استخدام البوت.\n\n"
            "يرجى إدخال رمز التحقق المكون من 6 أرقام الذي تم إرساله إلى بريدك الإلكتروني.\n\n"
            "إذا لم تستلم الرمز، يمكنك استخدام زر 'إعادة إرسال' أدناه.",
            reply_markup=get_verification_retry_keyboard()
        )
        await state.set_state(RegistrationStates.waiting_for_verification_code)
        return
    
    from handlers.keyboards import get_main_menu_keyboard
    await message.answer(
        f"✅ تم تسجيل الدخول بنجاح! مرحباً بعودتك، {user.full_name or 'المستخدم'}!",
        reply_markup=get_main_menu_keyboard(user.profile_completed)
    )
    await state.clear()

