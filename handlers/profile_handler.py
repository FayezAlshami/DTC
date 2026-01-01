"""Profile handler."""
from datetime import datetime
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_specialization_keyboard_with_ids, get_profile_keyboard
from handlers.common import require_auth
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Gender, ContactAccount
from services.profile_service import ProfileService
from repositories.user_repository import UserRepository
from repositories.specialization_repository import SpecializationRepository


router = Router()


class ProfileStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_student_choice = State()
    waiting_for_student_id = State()
    waiting_for_specialization = State()
    waiting_for_phone = State()
    waiting_for_dob = State()
    waiting_for_gender = State()
    # Contact accounts states
    waiting_for_contact_platform = State()
    waiting_for_contact_username = State()
    waiting_for_contact_url = State()


@router.message(F.text == "إكمال ملفك الشخصي")
@require_auth
async def start_profile_completion(message: Message, state: FSMContext, user: User, **kwargs):
    """Start profile completion."""
    if bool(user.profile_completed):
        await message.answer("ملفك الشخصي مكتمل بالفعل. استخدم 'عرض ملفك الشخصي' لعرضه.")
        return

    await message.answer(
        "دعنا نكمل ملفك الشخصي!\n\n"
        "يرجى إدخال اسمك الكامل:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ProfileStates.waiting_for_full_name)


@router.message(F.text == "عرض ملفك الشخصي")
@require_auth
async def view_profile(message: Message, user: User, db_session: AsyncSession, **kwargs):
    """View user profile."""
    profile_text = f"📋 ملفك الشخصي\n\n"
    
    # Basic info
    full_name = getattr(user, 'full_name', None)
    profile_text += f"- الاسم الكامل: {full_name if full_name not in [None, ''] else 'غير محدد'}\n"
    profile_text += f"- البريد الإلكتروني: {getattr(user, 'email', '')}\n"
    
    phone_number = getattr(user, 'phone_number', None)
    profile_text += f"- رقم الهاتف: {phone_number if phone_number not in [None, ''] else 'غير محدد'}\n"
    
    date_of_birth = getattr(user, 'date_of_birth', None)
    profile_text += f"- تاريخ الميلاد: {date_of_birth.strftime('%Y-%m-%d') if date_of_birth else 'غير محدد'}\n"
    
    gender = getattr(user, 'gender', None)
    gender_value = gender.value if gender is not None else 'غير محدد'
    profile_text += f"- الجنس: {gender_value}\n"

    # Student info
    if bool(user.is_student):
        profile_text += f"\n🎓 معلومات الطالب:\n"
        student_id = getattr(user, 'student_id', None)
        specialization = getattr(user, 'specialization', None)
        profile_text += f"- رقم الطالب: {student_id if student_id not in [None, ''] else 'غير محدد'}\n"
        profile_text += f"- التخصص: {specialization if specialization not in [None, ''] else 'غير محدد'}\n"

    # Profile completion status
    profile_text += f"\nحالة الملف الشخصي: {'✅ مكتمل' if bool(user.profile_completed) else '❌ غير مكتمل'}"

    # Get contact accounts
    from database.models import ContactAccount
    from sqlalchemy import select
    
    contact_accounts_query = select(ContactAccount).where(ContactAccount.user_id == user.id).order_by(ContactAccount.display_order.asc())
    result = await db_session.execute(contact_accounts_query)
    contact_accounts = result.scalars().all()
    
    # Create keyboard with contact accounts button
    keyboard = get_profile_keyboard(bool(user.profile_completed), len(contact_accounts) > 0)

    await message.answer(profile_text, reply_markup=keyboard)


@router.message(ProfileStates.waiting_for_full_name)
async def process_full_name(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process full name."""
    if not message.text:
        await message.answer("يرجى إدخال نص صحيح.")
        return
    
    if message.text == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إكمال الملف الشخصي.", reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value))
        return

    full_name = message.text.strip()
    if len(full_name) < 2 or len(full_name) > 255:
        await message.answer("يجب أن يكون الاسم الكامل بين 2 و 255 حرفاً. يرجى المحاولة مرة أخرى:")
        return

    await state.update_data(full_name=full_name)

    await message.answer(
        "هل تريد تقديم الخدمات كطالب؟\n\n"
        "إذا كانت الإجابة نعم، ستحتاج إلى تقديم رقم الطالب والتخصص.\n"
        "إذا كانت الإجابة لا، لا يزال بإمكانك تصفح وطلب الخدمات.\n\n"
        "أجب بـ 'نعم' أو 'لا':"
    )
    await state.set_state(ProfileStates.waiting_for_student_choice)


@router.message(ProfileStates.waiting_for_student_choice)
async def process_student_choice(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process student choice."""
    if not message.text:
        await message.answer("يرجى إدخال نص صحيح.")
        return
    
    if message.text.lower() in ["cancel", "إلغاء"]:
        await state.clear()
        await message.answer("تم إلغاء إكمال الملف الشخصي.", reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value))
        return

    if message.text.lower() in ["yes", "y", "نعم"]:
        await message.answer("يرجى إدخال رقم الطالب:")
        await state.set_state(ProfileStates.waiting_for_student_id)
    elif message.text.lower() in ["no", "n", "لا"]:
        await state.update_data(student_id=None, specialization=None, is_student=False)
        await message.answer("يرجى إدخال رقم هاتفك (اختياري، أو اكتب 'تخطي'):")
        await state.set_state(ProfileStates.waiting_for_phone)
    else:
        await message.answer("يرجى الرد بـ 'نعم' أو 'لا':")


@router.message(ProfileStates.waiting_for_student_id)
async def process_student_id(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process student ID."""
    if not message.text:
        await message.answer("يرجى إدخال نص صحيح.")
        return
    
    if message.text.lower() in ["cancel", "إلغاء"]:
        await state.clear()
        await message.answer("تم إلغاء إكمال الملف الشخصي.", reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value))
        return

    student_id = message.text.strip()
    
    # Validation for student ID
    if not student_id:
        await message.answer("❌ يرجى إدخال رقم الطالب.")
        return
    
    if len(student_id) < 3 or len(student_id) > 100:
        await message.answer("❌ يجب أن يكون رقم الطالب بين 3 و 100 حرف. يرجى المحاولة مرة أخرى:")
        return
    
    # تحقق من أن رقم الطالب يحتوي على أرقام أو أحرف صالحة فقط
    import re
    if not re.match(r'^[A-Za-z0-9\-_]+$', student_id):
        await message.answer("❌ رقم الطالب يحتوي على رموز غير مسموحة. يُسمح بالأرقام والأحرف فقط (A-Z, 0-9, -, _). يرجى المحاولة مرة أخرى:")
        return

    await state.update_data(student_id=student_id)
    
    # Get active specializations from database
    spec_repo = SpecializationRepository(db_session)
    specializations = await spec_repo.get_all_active()
    
    if not specializations:
        await message.answer(
            "⚠️ لا توجد اختصاصات متاحة حالياً.\n"
            "يرجى الاتصال بالمشرف لإضافة الاختصاصات."
        )
        return
    
    # Create list of (id, name) tuples for keyboard
    spec_list: list[tuple[int, str]] = []
    for spec in specializations:
        spec_id = getattr(spec, 'id', None)
        name = getattr(spec, 'name', None)
        if spec_id and name and isinstance(name, str):
            spec_list.append((int(spec_id), name))
    
    if not spec_list:
        await message.answer(
            "⚠️ لا توجد اختصاصات متاحة حالياً.\n"
            "يرجى الاتصال بالمشرف لإضافة الاختصاصات."
        )
        return
    
    await message.answer(
        "يرجى اختيار تخصصك/مجال دراستك من القائمة:",
        reply_markup=get_specialization_keyboard_with_ids(spec_list)
    )
    await state.set_state(ProfileStates.waiting_for_specialization)


@router.callback_query(F.data.startswith("select_spec_id:"), ProfileStates.waiting_for_specialization)
async def process_specialization_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process specialization selection from keyboard using ID."""
    if not callback.data:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return
    
    try:
        spec_id_str = callback.data.split(":", 1)[1]
        spec_id = int(spec_id_str)
    except (ValueError, IndexError):
        await callback.answer("⚠️ خطأ في بيانات الاختصاص.", show_alert=True)
        return
    
    # Verify specialization exists and is active
    spec_repo = SpecializationRepository(db_session)
    specialization = await spec_repo.get_by_id(spec_id)
    
    if not specialization:
        await callback.answer("⚠️ هذا الاختصاص غير موجود.", show_alert=True)
        return
    
    is_active = getattr(specialization, 'is_active', False)
    if not bool(is_active):
        await callback.answer("⚠️ هذا الاختصاص غير متاح حالياً.", show_alert=True)
        return
    
    spec_name = getattr(specialization, 'name', None)
    if not spec_name or not isinstance(spec_name, str):
        await callback.answer("⚠️ خطأ في بيانات الاختصاص.", show_alert=True)
        return
    
    await callback.answer()
    
    # Delete the message with keyboard
    try:
        if callback.message and hasattr(callback.message, 'delete'):
            await callback.message.delete()  # type: ignore
    except Exception:
        # If deletion fails (e.g., message too old), just continue
        pass
    
    await state.update_data(specialization=spec_name, is_student=True)
    
    # Send confirmation message - use bot from kwargs if available, otherwise use callback
    from aiogram import Bot
    bot: Bot = kwargs.get('bot') or callback.bot  # type: ignore
    
    await bot.send_message(
        callback.from_user.id,  # type: ignore
        f"✅ تم اختيار الاختصاص: {spec_name}\n\n"
        "يرجى إدخال رقم هاتفك (اختياري، أو اكتب 'تخطي'):"
    )
    
    await state.set_state(ProfileStates.waiting_for_phone)


@router.message(ProfileStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process phone number."""
    if not message.text:
        await message.answer("يرجى إدخال نص صحيح.")
        return
    
    if message.text.lower() in ["cancel", "إلغاء"]:
        await state.clear()
        await message.answer("تم إلغاء إكمال الملف الشخصي.", reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value))
        return

    phone: Optional[str] = None
    phone_input = message.text.strip()
    if phone_input.lower() not in ["skip", "تخطي"]:
        profile_service = ProfileService(db_session)
        if not profile_service.validate_phone(phone_input):
            await message.answer("صيغة رقم الهاتف غير صحيحة. يرجى المحاولة مرة أخرى أو اكتب 'تخطي':")
            return
        phone = phone_input

    await state.update_data(phone_number=phone)
    await message.answer("يرجى إدخال تاريخ ميلادك (صيغة YYYY-MM-DD، أو اكتب 'تخطي'):")
    await state.set_state(ProfileStates.waiting_for_dob)


@router.message(ProfileStates.waiting_for_dob)
async def process_dob(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process date of birth."""
    if not message.text:
        await message.answer("يرجى إدخال نص صحيح.")
        return
    
    if message.text.lower() in ["cancel", "إلغاء"]:
        await state.clear()
        await message.answer("تم إلغاء إكمال الملف الشخصي.", reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value))
        return

    dob: Optional[datetime] = None
    if message.text.lower() not in ["skip", "تخطي"]:
        try:
            dob = datetime.strptime(message.text.strip(), "%Y-%m-%d")
        except ValueError:
            await message.answer("صيغة التاريخ غير صحيحة. يرجى استخدام صيغة YYYY-MM-DD أو اكتب 'تخطي':")
            return

    await state.update_data(date_of_birth=dob)
    await message.answer(
        "يرجى اختيار جنسك:\n"
        "1. ذكر\n"
        "2. أنثى\n"
        "أو اكتب 'تخطي'"
    )
    await state.set_state(ProfileStates.waiting_for_gender)


@router.message(ProfileStates.waiting_for_gender)
async def process_gender(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process gender."""
    if not message.text:
        await message.answer("يرجى إدخال نص صحيح.")
        return
    
    if message.text.lower() in ["cancel", "إلغاء"]:
        await state.clear()
        await message.answer("تم إلغاء إكمال الملف الشخصي.", reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value))
        return

    gender: Optional[Gender] = None
    text_input = message.text.strip().lower()
    
    if text_input not in ["skip", "تخطي"]:
        if text_input in ["1", "ذكر", "male"]:
            gender = Gender.MALE
        elif text_input in ["2", "أنثى", "female"]:
            gender = Gender.FEMALE
        else:
            await message.answer(
                "خيار غير صحيح. يرجى اختيار:\n"
                "1. ذكر\n"
                "2. أنثى\n"
                "أو اكتب 'تخطي'"
            )
            return

    # جلب كل البيانات من الـ state
    data = await state.get_data()
    
    try:
        # تحديث بيانات المستخدم مع التحقق من القيم
        full_name = data.get('full_name')
        if full_name:
            user.full_name = full_name  # type: ignore
        
        # الحقول الاختيارية
        phone_number = data.get('phone_number')
        if phone_number is not None:
            user.phone_number = phone_number  # type: ignore
        
        date_of_birth = data.get('date_of_birth')
        if date_of_birth is not None:
            user.date_of_birth = date_of_birth  # type: ignore
        
        if gender is not None:
            user.gender = gender  # type: ignore
        
        # إذا اختار يكون طالب
        is_student = data.get('is_student', False)
        if is_student:
            user.is_student = True  # type: ignore
            student_id = data.get('student_id')
            specialization = data.get('specialization')
            
            if student_id:
                user.student_id = student_id  # type: ignore
            if specialization:
                user.specialization = specialization  # type: ignore
        
        # تحديد الملف كمكتمل
        user.profile_completed = True  # type: ignore
        
        await db_session.commit()
        await db_session.refresh(user)
        
        await state.clear()
        await message.answer(
            "✅ تم إكمال ملفك الشخصي بنجاح!\n\n"
            "يمكنك الآن استخدام جميع ميزات البوت.",
            reply_markup=get_main_menu_keyboard(True, user.role.value)
        )
        
    except Exception as e:
        await db_session.rollback()
        await message.answer(
            "❌ حدث خطأ أثناء حفظ البيانات. يرجى المحاولة مرة أخرى.\n"
            f"الخطأ: {str(e)}"
        )


# Contact Accounts Handlers
PLATFORMS = ["فيسبوك", "تلجرام", "واتساب", "إنستغرام", "تويتر", "لينكد إن", "أخرى"]


@router.callback_query(F.data == "add_contact_accounts")
@require_auth
async def start_add_contact_account(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Start adding contact account flow."""
    await callback.answer()
    
    # Get existing platforms for this user
    from sqlalchemy import select
    existing_accounts_query = select(ContactAccount.platform).where(ContactAccount.user_id == user.id)
    result = await db_session.execute(existing_accounts_query)
    existing_platforms = {row[0] for row in result.fetchall()}
    
    keyboard = InlineKeyboardBuilder()
    for platform in PLATFORMS:
        if platform not in existing_platforms:
            keyboard.add(InlineKeyboardButton(text=platform, callback_data=f"select_platform:{platform}"))
        else:
            # Show platform as disabled (already added)
            keyboard.add(InlineKeyboardButton(text=f"✓ {platform} (مضاف)", callback_data="platform_already_added"))
    keyboard.add(InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_add_account"))
    keyboard.adjust(2)
    
    if callback.message:
        await callback.message.answer(
            "اختر منصة التواصل التي تريد إضافتها:",
            reply_markup=keyboard.as_markup()
        )
    await state.set_state(ProfileStates.waiting_for_contact_platform)


@router.callback_query(F.data.startswith("select_platform:"))
@require_auth
async def process_platform_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process platform selection."""
    if not callback.data:
        return
    
    platform = callback.data.split(":", 1)[1]
    
    # Check if platform already exists for this user
    from sqlalchemy import select
    existing_query = select(ContactAccount).where(
        ContactAccount.user_id == user.id,
        ContactAccount.platform == platform
    )
    result = await db_session.execute(existing_query)
    existing_account = result.scalar_one_or_none()
    
    if existing_account:
        await callback.answer("هذه المنصة مضاف لها حساب بالفعل. يمكنك حذف الحساب القديم أولاً.", show_alert=True)
        return
    
    await state.update_data(platform=platform)
    await callback.answer()
    
    if callback.message:
        await callback.message.answer(
            f"تم اختيار: {platform}\n\n"
            "أدخل اسم المستخدم أو المعرف (مثال: @username أو username):\n"
            "أو اكتب 'تخطي' إذا لم يكن لديك",
            reply_markup=get_cancel_keyboard()
        )
    await state.set_state(ProfileStates.waiting_for_contact_username)


@router.callback_query(F.data == "platform_already_added")
@require_auth
async def platform_already_added(callback: CallbackQuery, **kwargs):
    """Handle click on already added platform."""
    await callback.answer("هذه المنصة مضاف لها حساب بالفعل. يمكنك حذف الحساب القديم أولاً.", show_alert=True)


@router.callback_query(F.data == "cancel_add_account")
@require_auth
async def cancel_add_account(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Cancel adding contact account."""
    await state.clear()
    await callback.answer("تم الإلغاء")
    # Delete the message with the keyboard
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            # If deletion fails, just answer
            pass


@router.message(ProfileStates.waiting_for_contact_username)
@require_auth
async def process_contact_username(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process contact username."""
    if message.text and message.text.lower() in ["إلغاء", "cancel"]:
        await state.clear()
        await message.answer("تم إلغاء إضافة حساب التواصل.")
        return
    
    username = None
    if message.text and message.text.lower() not in ["تخطي", "skip"]:
        username = message.text.strip()
    
    await state.update_data(username=username)
    await message.answer(
        "أدخل رابط الحساب الكامل (مثال: https://facebook.com/username):\n"
        "أو اكتب 'تخطي' إذا لم يكن لديك رابط",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ProfileStates.waiting_for_contact_url)


@router.message(ProfileStates.waiting_for_contact_url)
@require_auth
async def process_contact_url(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process contact URL and save account."""
    if message.text and message.text.lower() in ["إلغاء", "cancel"]:
        await state.clear()
        await message.answer("تم إلغاء إضافة حساب التواصل.")
        return
    
    url = None
    if message.text and message.text.lower() not in ["تخطي", "skip"]:
        url = message.text.strip()
        # Validate URL format
        if not (url.startswith("http://") or url.startswith("https://")):
            await message.answer("يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://")
            return
    
    data = await state.get_data()
    platform = data.get("platform")
    username = data.get("username")
    
    if not platform:
        await message.answer("حدث خطأ. يرجى المحاولة مرة أخرى.")
        await state.clear()
        return
    
    # Check if platform already exists for this user (double check before saving)
    from sqlalchemy import select
    existing_query = select(ContactAccount).where(
        ContactAccount.user_id == user.id,
        ContactAccount.platform == platform
    )
    result = await db_session.execute(existing_query)
    existing_account = result.scalar_one_or_none()
    
    if existing_account:
        await message.answer(
            f"❌ هذه المنصة ({platform}) مضاف لها حساب بالفعل.\n\n"
            "يمكنك حذف الحساب القديم أولاً من خلال 'إدارة حسابات التواصل'."
        )
        await state.clear()
        return
    
    # Get current accounts count for display_order
    from sqlalchemy import func
    count_result = await db_session.execute(
        select(func.count(ContactAccount.id)).where(ContactAccount.user_id == user.id)
    )
    display_order = count_result.scalar() or 0
    
    # Create contact account
    contact_account = ContactAccount(
        user_id=user.id,  # type: ignore
        platform=platform,
        username=username,
        url=url,
        display_order=display_order
    )
    
    db_session.add(contact_account)
    await db_session.commit()
    await db_session.refresh(contact_account)
    
    await state.clear()
    await message.answer(
        f"✅ تم إضافة حساب {platform} بنجاح!\n\n"
        f"المستخدم: {username or 'غير محدد'}\n"
        f"الرابط: {url or 'غير محدد'}",
        reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value)
    )


@router.callback_query(F.data == "manage_contact_accounts")
@require_auth
async def manage_contact_accounts(callback: CallbackQuery, db_session: AsyncSession, user: User, **kwargs):
    """Show and manage contact accounts."""
    await callback.answer()
    
    from sqlalchemy import select
    accounts_query = select(ContactAccount).where(ContactAccount.user_id == user.id).order_by(ContactAccount.display_order.asc())
    result = await db_session.execute(accounts_query)
    accounts = result.scalars().all()
    
    if not accounts:
        if callback.message:
            await callback.message.answer("لا توجد حسابات تواصل مضافة.")
        return
    
    accounts_text = "📱 حسابات التواصل:\n\n"
    keyboard = InlineKeyboardBuilder()
    
    for account in accounts:
        platform = getattr(account, 'platform', 'غير معروف')
        username = getattr(account, 'username', None)
        account_id = getattr(account, 'id', None)
        
        accounts_text += f"• {platform}"
        if username:
            accounts_text += f": {username}"
        accounts_text += "\n"
        
        if account_id:
            keyboard.add(InlineKeyboardButton(
                text=f"🗑️ حذف {platform}",
                callback_data=f"delete_account:{account_id}"
            ))
    
    keyboard.add(InlineKeyboardButton(text="➕ إضافة حساب جديد", callback_data="add_contact_accounts"))
    keyboard.adjust(1)
    
    if callback.message:
        await callback.message.answer(accounts_text, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.startswith("delete_account:"))
@require_auth
async def delete_contact_account(callback: CallbackQuery, db_session: AsyncSession, user: User, **kwargs):
    """Delete a contact account."""
    if not callback.data:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return
    
    try:
        account_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("خطأ في بيانات الحساب.", show_alert=True)
        return
    
    from sqlalchemy import select
    account_query = select(ContactAccount).where(
        ContactAccount.id == account_id,
        ContactAccount.user_id == user.id
    )
    result = await db_session.execute(account_query)
    account = result.scalar_one_or_none()
    
    if not account:
        await callback.answer("الحساب غير موجود.", show_alert=True)
        return
    
    platform = getattr(account, 'platform', 'غير معروف')
    await db_session.delete(account)
    await db_session.commit()
    
    await callback.answer(f"تم حذف حساب {platform}")
    if callback.message:
        from aiogram import Bot
        bot: Bot = kwargs.get('bot') or callback.bot  # type: ignore
        await bot.send_message(
            callback.from_user.id,  # type: ignore
            f"✅ تم حذف حساب {platform} بنجاح."
        )
