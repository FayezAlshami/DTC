"""Start command handler with complete registration flow."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import (
    get_start_keyboard, get_main_menu_keyboard, get_verification_retry_keyboard,
    get_role_selection_keyboard, get_gender_keyboard, get_skip_keyboard,
    get_single_specialization_keyboard, get_multi_specialization_keyboard,
    get_subjects_keyboard
)
from handlers.common import require_auth
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user_repository import UserRepository
from repositories.specialization_repository import SpecializationRepository
from repositories.subject_repository import SubjectRepository
from repositories.teacher_repository import TeacherRepository
from database.models import User, UserRole, Gender
from datetime import datetime

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_verification_code = State()
    # Role selection
    waiting_for_role = State()
    # Student states
    waiting_for_student_name = State()
    waiting_for_student_specialization = State()
    waiting_for_student_number = State()
    waiting_for_student_dob = State()
    waiting_for_student_gender = State()
    # Teacher states
    waiting_for_teacher_name = State()
    waiting_for_teacher_specializations = State()
    waiting_for_teacher_number = State()
    waiting_for_teacher_dob = State()
    waiting_for_teacher_gender = State()
    waiting_for_teacher_subjects = State()
    # Visitor states
    waiting_for_visitor_name = State()
    waiting_for_visitor_number = State()
    waiting_for_visitor_gender = State()


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
    
    # OTP verified - now ask for role selection
    await message.answer(
        "✅ تم التحقق من بريدك الإلكتروني بنجاح!\n\n"
        "الآن يرجى تحديد نوع حسابك:",
        reply_markup=get_role_selection_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_role)


# ==================== ROLE SELECTION ====================

@router.message(RegistrationStates.waiting_for_role)
async def process_role_selection(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process role selection."""
    role_text = message.text
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await message.answer("انتهت الجلسة. يرجى البدء من جديد باستخدام /start")
        await state.clear()
        return
    
    if role_text == "🎓 طالب":
        await state.update_data(selected_role="student")
        await message.answer("يرجى إدخال اسمك الكامل:", reply_markup=None)
        await state.set_state(RegistrationStates.waiting_for_student_name)
        
    elif role_text == "👨‍🏫 أستاذ":
        await state.update_data(selected_role="teacher")
        await message.answer("يرجى إدخال اسمك الكامل:", reply_markup=None)
        await state.set_state(RegistrationStates.waiting_for_teacher_name)
        
    elif role_text == "👤 زائر":
        await state.update_data(selected_role="visitor")
        await message.answer("يرجى إدخال اسمك الكامل:", reply_markup=None)
        await state.set_state(RegistrationStates.waiting_for_visitor_name)
        
    else:
        await message.answer(
            "يرجى اختيار نوع الحساب من الأزرار أدناه:",
            reply_markup=get_role_selection_keyboard()
        )


# ==================== STUDENT REGISTRATION ====================

@router.message(RegistrationStates.waiting_for_student_name)
async def process_student_name(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process student name."""
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        await message.answer("يجب أن يكون الاسم 3 أحرف على الأقل. يرجى المحاولة مرة أخرى:")
        return
    
    await state.update_data(full_name=full_name)
    
    # Get specializations
    spec_repo = SpecializationRepository(db_session)
    specs = await spec_repo.get_all_active()
    
    if not specs:
        await message.answer("لا توجد تخصصات متاحة حالياً. يرجى التواصل مع الإدارة.")
        await state.clear()
        return
    
    spec_list = [(s.id, s.name) for s in specs]
    
    await message.answer(
        "يرجى اختيار تخصصك:",
        reply_markup=get_single_specialization_keyboard(spec_list)
    )
    await state.set_state(RegistrationStates.waiting_for_student_specialization)


@router.callback_query(F.data.startswith("reg_spec:"), RegistrationStates.waiting_for_student_specialization)
async def process_student_specialization_callback(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Process student specialization selection."""
    spec_id = int(callback.data.split(":")[1])
    
    # Get specialization name
    spec_repo = SpecializationRepository(db_session)
    spec = await spec_repo.get_by_id(spec_id)
    
    if not spec:
        await callback.answer("التخصص غير موجود!")
        return
    
    await state.update_data(specialization_id=spec_id, specialization_name=spec.name)
    await callback.message.edit_text(f"✅ تم اختيار التخصص: {spec.name}")
    
    await callback.message.answer("يرجى إدخال رقم الطالب:")
    await state.set_state(RegistrationStates.waiting_for_student_number)
    await callback.answer()


@router.message(RegistrationStates.waiting_for_student_number)
async def process_student_number(message: Message, state: FSMContext):
    """Process student number."""
    student_number = message.text.strip()
    
    if len(student_number) < 1:
        await message.answer("يرجى إدخال رقم الطالب:")
        return
    
    await state.update_data(student_number=student_number)
    await message.answer(
        "يرجى إدخال تاريخ ميلادك (صيغة YYYY-MM-DD):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_student_dob)


@router.message(RegistrationStates.waiting_for_student_dob)
async def process_student_dob(message: Message, state: FSMContext):
    """Process student date of birth."""
    dob_text = message.text.strip()
    
    if dob_text == "تخطي":
        await state.update_data(date_of_birth=None)
    else:
        try:
            dob = datetime.strptime(dob_text, "%Y-%m-%d")
            await state.update_data(date_of_birth=dob)
        except ValueError:
            await message.answer(
                "صيغة التاريخ غير صحيحة. يرجى استخدام صيغة YYYY-MM-DD (مثال: 2000-01-15):",
                reply_markup=get_skip_keyboard()
            )
            return
    
    await message.answer("يرجى اختيار جنسك:", reply_markup=get_gender_keyboard())
    await state.set_state(RegistrationStates.waiting_for_student_gender)


@router.message(RegistrationStates.waiting_for_student_gender)
async def process_student_gender(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process student gender and complete registration."""
    gender_text = message.text.strip()
    
    if gender_text == "ذكر":
        gender = Gender.MALE
    elif gender_text == "أنثى":
        gender = Gender.FEMALE
    else:
        await message.answer("يرجى اختيار جنسك من الأزرار:", reply_markup=get_gender_keyboard())
        return
    
    # Save all student data
    data = await state.get_data()
    user_id = data.get("user_id")
    
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        await message.answer("حدث خطأ. يرجى البدء من جديد باستخدام /start")
        await state.clear()
        return
    
    # Update user
    user.role = UserRole.STUDENT
    user.is_student = True
    user.full_name = data.get("full_name")
    user.specialization = data.get("specialization_name")
    user.specialization_id = data.get("specialization_id")
    user.student_id = data.get("student_number")
    user.date_of_birth = data.get("date_of_birth")
    user.gender = gender
    user.profile_completed = True
    
    await db_session.commit()
    
    await message.answer(
        "✅ تم إنشاء حسابك كطالب بنجاح!\n\n"
        f"📋 ملخص المعلومات:\n"
        f"• الاسم: {user.full_name}\n"
        f"• التخصص: {user.specialization}\n"
        f"• رقم الطالب: {user.student_id}\n"
        f"• الجنس: {'ذكر' if gender == Gender.MALE else 'أنثى'}\n\n"
        "مرحباً بك في بوت DTC Job!",
        reply_markup=get_main_menu_keyboard(True)
    )
    await state.clear()


# ==================== TEACHER REGISTRATION ====================

@router.message(RegistrationStates.waiting_for_teacher_name)
async def process_teacher_name(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process teacher name."""
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        await message.answer("يجب أن يكون الاسم 3 أحرف على الأقل. يرجى المحاولة مرة أخرى:")
        return
    
    await state.update_data(full_name=full_name, selected_spec_ids=[])
    
    # Get specializations
    spec_repo = SpecializationRepository(db_session)
    specs = await spec_repo.get_all_active()
    
    if not specs:
        await message.answer("لا توجد تخصصات متاحة حالياً. يرجى التواصل مع الإدارة.")
        await state.clear()
        return
    
    spec_list = [(s.id, s.name) for s in specs]
    await state.update_data(available_specs=spec_list)
    
    await message.answer(
        "يرجى اختيار تخصصاتك (يمكنك اختيار أكثر من تخصص):\n\n"
        "اضغط على التخصص لتحديده أو إلغاء تحديده، ثم اضغط 'تأكيد الاختيار'.",
        reply_markup=get_multi_specialization_keyboard(spec_list, [])
    )
    await state.set_state(RegistrationStates.waiting_for_teacher_specializations)


@router.callback_query(F.data.startswith("reg_multi_spec:"), RegistrationStates.waiting_for_teacher_specializations)
async def process_teacher_spec_toggle(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Toggle teacher specialization selection."""
    spec_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    selected_ids = data.get("selected_spec_ids", [])
    available_specs = data.get("available_specs", [])
    
    if spec_id in selected_ids:
        selected_ids.remove(spec_id)
    else:
        selected_ids.append(spec_id)
    
    await state.update_data(selected_spec_ids=selected_ids)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_multi_specialization_keyboard(available_specs, selected_ids)
    )
    await callback.answer()


@router.callback_query(F.data == "reg_spec_confirm", RegistrationStates.waiting_for_teacher_specializations)
async def process_teacher_spec_confirm(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Confirm teacher specialization selection."""
    data = await state.get_data()
    selected_ids = data.get("selected_spec_ids", [])
    
    if not selected_ids:
        await callback.answer("يرجى اختيار تخصص واحد على الأقل!")
        return
    
    # Get specialization names
    spec_repo = SpecializationRepository(db_session)
    spec_names = []
    for spec_id in selected_ids:
        spec = await spec_repo.get_by_id(spec_id)
        if spec:
            spec_names.append(spec.name)
    
    await state.update_data(specialization_names=spec_names)
    await callback.message.edit_text(f"✅ تم اختيار التخصصات: {', '.join(spec_names)}")
    
    await callback.message.answer("يرجى إدخال رقم الأستاذ:")
    await state.set_state(RegistrationStates.waiting_for_teacher_number)
    await callback.answer()


@router.message(RegistrationStates.waiting_for_teacher_number)
async def process_teacher_number(message: Message, state: FSMContext):
    """Process teacher number."""
    teacher_number = message.text.strip()
    
    if len(teacher_number) < 1:
        await message.answer("يرجى إدخال رقم الأستاذ:")
        return
    
    await state.update_data(teacher_number=teacher_number)
    await message.answer(
        "يرجى إدخال تاريخ ميلادك (صيغة YYYY-MM-DD):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_teacher_dob)


@router.message(RegistrationStates.waiting_for_teacher_dob)
async def process_teacher_dob(message: Message, state: FSMContext):
    """Process teacher date of birth."""
    dob_text = message.text.strip()
    
    if dob_text == "تخطي":
        await state.update_data(date_of_birth=None)
    else:
        try:
            dob = datetime.strptime(dob_text, "%Y-%m-%d")
            await state.update_data(date_of_birth=dob)
        except ValueError:
            await message.answer(
                "صيغة التاريخ غير صحيحة. يرجى استخدام صيغة YYYY-MM-DD (مثال: 1985-05-20):",
                reply_markup=get_skip_keyboard()
            )
            return
    
    await message.answer("يرجى اختيار جنسك:", reply_markup=get_gender_keyboard())
    await state.set_state(RegistrationStates.waiting_for_teacher_gender)


@router.message(RegistrationStates.waiting_for_teacher_gender)
async def process_teacher_gender(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process teacher gender and show subjects selection."""
    gender_text = message.text.strip()
    
    if gender_text == "ذكر":
        gender = Gender.MALE
    elif gender_text == "أنثى":
        gender = Gender.FEMALE
    else:
        await message.answer("يرجى اختيار جنسك من الأزرار:", reply_markup=get_gender_keyboard())
        return
    
    await state.update_data(gender=gender)
    
    # Get available subjects for selected specializations
    data = await state.get_data()
    selected_spec_ids = data.get("selected_spec_ids", [])
    
    subject_repo = SubjectRepository(db_session)
    available_subjects = await subject_repo.get_unassigned_subjects_by_specializations(selected_spec_ids)
    
    if not available_subjects:
        # No subjects available, complete registration without subjects
        await complete_teacher_registration(message, state, db_session)
        return
    
    subject_list = [(s.id, f"{s.name} ({s.specialization.name})") for s in available_subjects]
    await state.update_data(available_subjects=subject_list, selected_subject_ids=[])
    
    await message.answer(
        "يرجى اختيار المواد التي تدرسها:\n\n"
        "اضغط على المادة لتحديدها أو إلغاء تحديدها، ثم اضغط 'تأكيد الاختيار'.\n"
        "يمكنك أيضاً تخطي هذه الخطوة.",
        reply_markup=get_subjects_keyboard(subject_list, [])
    )
    await state.set_state(RegistrationStates.waiting_for_teacher_subjects)


@router.callback_query(F.data.startswith("reg_subject:"), RegistrationStates.waiting_for_teacher_subjects)
async def process_teacher_subject_toggle(callback: CallbackQuery, state: FSMContext):
    """Toggle teacher subject selection."""
    subject_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    selected_ids = data.get("selected_subject_ids", [])
    available_subjects = data.get("available_subjects", [])
    
    if subject_id in selected_ids:
        selected_ids.remove(subject_id)
    else:
        selected_ids.append(subject_id)
    
    await state.update_data(selected_subject_ids=selected_ids)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_subjects_keyboard(available_subjects, selected_ids)
    )
    await callback.answer()


@router.callback_query(F.data == "reg_subjects_confirm", RegistrationStates.waiting_for_teacher_subjects)
async def process_teacher_subjects_confirm(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Confirm teacher subjects selection."""
    await callback.message.edit_text("✅ تم اختيار المواد")
    await complete_teacher_registration(callback.message, state, db_session)
    await callback.answer()


@router.callback_query(F.data == "reg_subjects_skip", RegistrationStates.waiting_for_teacher_subjects)
async def process_teacher_subjects_skip(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Skip teacher subjects selection."""
    await state.update_data(selected_subject_ids=[])
    await callback.message.edit_text("تم تخطي اختيار المواد")
    await complete_teacher_registration(callback.message, state, db_session)
    await callback.answer()


async def complete_teacher_registration(message: Message, state: FSMContext, db_session: AsyncSession):
    """Complete teacher registration and save all data."""
    data = await state.get_data()
    user_id = data.get("user_id")
    
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        await message.answer("حدث خطأ. يرجى البدء من جديد باستخدام /start")
        await state.clear()
        return
    
    # Update user
    user.role = UserRole.TEACHER
    user.full_name = data.get("full_name")
    user.teacher_number = data.get("teacher_number")
    user.date_of_birth = data.get("date_of_birth")
    user.gender = data.get("gender")
    user.profile_completed = True
    
    # Set first specialization as main specialization
    spec_names = data.get("specialization_names", [])
    selected_spec_ids = data.get("selected_spec_ids", [])
    if spec_names:
        user.specialization = spec_names[0]
    if selected_spec_ids:
        user.specialization_id = selected_spec_ids[0]
    
    await db_session.commit()
    
    # Add teacher specializations
    teacher_repo = TeacherRepository(db_session)
    for i, spec_id in enumerate(selected_spec_ids):
        await teacher_repo.add_specialization(user_id, spec_id, is_primary=(i == 0))
    
    # Add teacher subjects
    selected_subject_ids = data.get("selected_subject_ids", [])
    for subject_id in selected_subject_ids:
        await teacher_repo.add_subject(user_id, subject_id)
    
    gender = data.get("gender")
    gender_text = 'ذكر' if gender == Gender.MALE else 'أنثى'
    
    summary = (
        "✅ تم إنشاء حسابك كأستاذ بنجاح!\n\n"
        f"📋 ملخص المعلومات:\n"
        f"• الاسم: {user.full_name}\n"
        f"• رقم الأستاذ: {user.teacher_number}\n"
        f"• التخصصات: {', '.join(spec_names)}\n"
        f"• الجنس: {gender_text}\n"
    )
    
    if selected_subject_ids:
        # Get subject names
        subject_repo = SubjectRepository(db_session)
        subject_names = []
        for sid in selected_subject_ids:
            subj = await subject_repo.get_by_id(sid)
            if subj:
                subject_names.append(subj.name)
        summary += f"• المواد: {', '.join(subject_names)}\n"
    
    summary += "\nمرحباً بك في بوت DTC Job!"
    
    await message.answer(summary, reply_markup=get_main_menu_keyboard(True))
    await state.clear()


# ==================== VISITOR REGISTRATION ====================

@router.message(RegistrationStates.waiting_for_visitor_name)
async def process_visitor_name(message: Message, state: FSMContext):
    """Process visitor name."""
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        await message.answer("يجب أن يكون الاسم 3 أحرف على الأقل. يرجى المحاولة مرة أخرى:")
        return
    
    await state.update_data(full_name=full_name)
    await message.answer("يرجى إدخال رقم الزائر:")
    await state.set_state(RegistrationStates.waiting_for_visitor_number)


@router.message(RegistrationStates.waiting_for_visitor_number)
async def process_visitor_number(message: Message, state: FSMContext):
    """Process visitor number."""
    visitor_number = message.text.strip()
    
    if len(visitor_number) < 1:
        await message.answer("يرجى إدخال رقم الزائر:")
        return
    
    await state.update_data(visitor_number=visitor_number)
    await message.answer("يرجى اختيار جنسك:", reply_markup=get_gender_keyboard())
    await state.set_state(RegistrationStates.waiting_for_visitor_gender)


@router.message(RegistrationStates.waiting_for_visitor_gender)
async def process_visitor_gender(message: Message, state: FSMContext, db_session: AsyncSession):
    """Process visitor gender and complete registration."""
    gender_text = message.text.strip()
    
    if gender_text == "ذكر":
        gender = Gender.MALE
    elif gender_text == "أنثى":
        gender = Gender.FEMALE
    else:
        await message.answer("يرجى اختيار جنسك من الأزرار:", reply_markup=get_gender_keyboard())
        return
    
    # Save all visitor data
    data = await state.get_data()
    user_id = data.get("user_id")
    
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        await message.answer("حدث خطأ. يرجى البدء من جديد باستخدام /start")
        await state.clear()
        return
    
    # Update user
    user.role = UserRole.VISITOR
    user.full_name = data.get("full_name")
    user.visitor_number = data.get("visitor_number")
    user.gender = gender
    user.profile_completed = True
    
    await db_session.commit()
    
    await message.answer(
        "✅ تم إنشاء حسابك كزائر بنجاح!\n\n"
        f"📋 ملخص المعلومات:\n"
        f"• الاسم: {user.full_name}\n"
        f"• رقم الزائر: {user.visitor_number}\n"
        f"• الجنس: {'ذكر' if gender == Gender.MALE else 'أنثى'}\n\n"
        "مرحباً بك في بوت DTC Job!",
        reply_markup=get_main_menu_keyboard(True)
    )
    await state.clear()


# ==================== LOGIN ====================

@router.message((F.text.lower() == "resend") | (F.text == "إعادة إرسال"))
async def resend_code(message: Message, state: FSMContext, db_session: AsyncSession):
    """Resend verification code (handles messages outside verification state)."""
    current_state = await state.get_state()
    
    # If we're in verification state, process_verification_code will handle it
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
    
    # Check if profile is completed (role selected)
    if not user.profile_completed:
        # User verified but didn't complete profile - redirect to role selection
        user_id: int = user.id  # type: ignore[assignment]
        await state.update_data(user_id=user_id)
        
        await message.answer(
            "مرحباً بك! لم تكمل ملفك الشخصي بعد.\n\n"
            "يرجى تحديد نوع حسابك:",
            reply_markup=get_role_selection_keyboard()
        )
        await state.set_state(RegistrationStates.waiting_for_role)
        return
    
    await message.answer(
        f"✅ تم تسجيل الدخول بنجاح! مرحباً بعودتك، {user.full_name or 'المستخدم'}!",
        reply_markup=get_main_menu_keyboard(user.profile_completed)
    )
    await state.clear()
