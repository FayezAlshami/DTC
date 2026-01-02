"""Keyboard builders."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_start_keyboard() -> ReplyKeyboardMarkup:
    """Get start menu keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="تسجيل الدخول"))
    builder.add(KeyboardButton(text="إنشاء حساب جديد"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_main_menu_keyboard(profile_completed: bool = False, user_role: str = "USER", is_student: bool = False) -> ReplyKeyboardMarkup:
    """Get main menu keyboard based on user role.
    
    Args:
        profile_completed: Whether user has completed their profile
        user_role: User role - "VISITOR", "TEACHER", "ADMIN", "USER"
        is_student: Whether user is a student (for USER role)
    """
    builder = ReplyKeyboardBuilder()
    
    # Common for all roles
    builder.add(KeyboardButton(text="💼 الوظائف"))
    
    # E-Learning - for students (USER with is_student=True), TEACHER, ADMIN (not VISITOR)
    if is_student or user_role in ("TEACHER", "ADMIN"):
        builder.add(KeyboardButton(text="🎓 التعلّم الإلكتروني"))
    
    # Social media - for all
    builder.add(KeyboardButton(text="📱 التواصل الاجتماعي"))
    
    # Yearly comparisons - for all
    builder.add(KeyboardButton(text="📊 مفاضلات العام"))
    
    # Teacher control panel - only for TEACHER
    if user_role == "TEACHER":
        builder.add(KeyboardButton(text="👨‍🏫 لوحة الأستاذ"))
    
    # Settings - for all
    builder.add(KeyboardButton(text="⚙️ الإعدادات"))
    
    # Profile button
    if profile_completed:
        builder.add(KeyboardButton(text="عرض ملفك الشخصي"))
    else:
        builder.add(KeyboardButton(text="إكمال ملفك الشخصي"))
    
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_jobs_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get jobs submenu keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="تقديم خدمة"))
    builder.add(KeyboardButton(text="طلب خدمة"))
    builder.add(KeyboardButton(text="سجلاتك"))
    builder.add(KeyboardButton(text="🔙 العودة للقائمة الرئيسية"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Get cancel keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="إلغاء"))
    return builder.as_markup(resize_keyboard=True)


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Get yes/no keyboard."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="نعم", callback_data="yes"))
    builder.add(InlineKeyboardButton(text="لا", callback_data="no"))
    return builder.as_markup()


def get_accept_reject_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Get accept/reject keyboard for contact requests."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="قبول", callback_data=f"accept_contact:{request_id}"))
    builder.add(InlineKeyboardButton(text="رفض", callback_data=f"reject_contact:{request_id}"))
    return builder.as_markup()


def get_service_contact_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for requesting contact with service provider."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="طلب التواصل",
        callback_data=f"request_service_contact:{service_id}"
    ))
    return builder.as_markup()


def get_request_offer_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for offering to provide a requested service."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="تقديم هذه الخدمة",
        callback_data=f"offer_service:{request_id}"
    ))
    return builder.as_markup()


def get_pagination_keyboard(page: int, total_pages: int, prefix: str, extra_data: str = "") -> InlineKeyboardMarkup:
    """Get pagination keyboard."""
    builder = InlineKeyboardBuilder()
    
    if page > 1:
        builder.add(InlineKeyboardButton(text="◀ السابق", callback_data=f"{prefix}:page:{page-1}:{extra_data}"))
    if page < total_pages:
        builder.add(InlineKeyboardButton(text="التالي ▶", callback_data=f"{prefix}:page:{page+1}:{extra_data}"))
    
    builder.adjust(2)
    return builder.as_markup()


def get_specialization_keyboard(specializations: list[str]) -> InlineKeyboardMarkup:
    """Get specialization selection keyboard."""
    builder = InlineKeyboardBuilder()
    for spec in specializations:
        builder.add(InlineKeyboardButton(text=spec, callback_data=f"select_spec:{spec}"))
    builder.adjust(2)
    return builder.as_markup()


def get_specialization_keyboard_with_ids(specs: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Get specialization selection keyboard using IDs."""
    builder = InlineKeyboardBuilder()
    for spec_id, spec_name in specs:
        # Use ID instead of name for callback_data to avoid encoding issues
        builder.add(InlineKeyboardButton(text=spec_name, callback_data=f"select_spec_id:{spec_id}"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get admin menu keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="إدارة الخدمات"))
    builder.add(KeyboardButton(text="إدارة الطلبات"))
    builder.add(KeyboardButton(text="إدارة المستخدمين"))
    builder.add(KeyboardButton(text="البث"))
    builder.add(KeyboardButton(text="الإحصائيات"))
    builder.add(KeyboardButton(text="عرض السجلات"))
    builder.add(KeyboardButton(text="العودة للقائمة الرئيسية"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_admin_approval_keyboard(item_id: int, item_type: str) -> InlineKeyboardMarkup:
    """Get admin approval keyboard for services/requests."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ قبول",
        callback_data=f"admin_approve:{item_type}:{item_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ رفض",
        callback_data=f"admin_reject:{item_type}:{item_id}"
    ))
    return builder.as_markup()


def get_profile_keyboard(profile_completed: bool = False, has_contact_accounts: bool = False) -> InlineKeyboardMarkup:
    """Get profile view keyboard with edit buttons and contact accounts."""
    builder = InlineKeyboardBuilder()
    
    # Edit profile buttons
    builder.add(InlineKeyboardButton(
        text="✏️ تعديل الاسم",
        callback_data="edit_profile_full_name"
    ))
    builder.add(InlineKeyboardButton(
        text="⚧️ تعديل الجنس",
        callback_data="edit_profile_gender"
    ))
    builder.add(InlineKeyboardButton(
        text="📱 تعديل رقم الهاتف",
        callback_data="edit_profile_phone"
    ))
    builder.add(InlineKeyboardButton(
        text="📅 تعديل تاريخ الميلاد",
        callback_data="edit_profile_dob"
    ))
    
    # Contact accounts buttons
    builder.add(InlineKeyboardButton(
        text="➕ إضافة حسابات تواصل",
        callback_data="add_contact_accounts"
    ))
    if has_contact_accounts:
        builder.add(InlineKeyboardButton(
            text="📱 إدارة حسابات التواصل",
            callback_data="manage_contact_accounts"
        ))
    
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_verification_retry_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard for verification code retry options."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="إعادة إرسال"))
    builder.add(KeyboardButton(text="إعادة إدخال عنوان البريد الإلكتروني"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_role_selection_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard for role selection during registration."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎓 طالب"))
    builder.add(KeyboardButton(text="👨‍🏫 أستاذ"))
    builder.add(KeyboardButton(text="👤 زائر"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_gender_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard for gender selection."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="ذكر"))
    builder.add(KeyboardButton(text="أنثى"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard with skip option."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="تخطي"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_single_specialization_keyboard(specs: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Get specialization selection keyboard for single selection (students)."""
    builder = InlineKeyboardBuilder()
    for spec_id, spec_name in specs:
        builder.add(InlineKeyboardButton(text=spec_name, callback_data=f"reg_spec:{spec_id}"))
    builder.adjust(2)
    return builder.as_markup()


def get_multi_specialization_keyboard(specs: list[tuple[int, str]], selected_ids: list[int] = None) -> InlineKeyboardMarkup:
    """Get specialization selection keyboard for multiple selection (teachers)."""
    selected_ids = selected_ids or []
    builder = InlineKeyboardBuilder()
    
    for spec_id, spec_name in specs:
        if spec_id in selected_ids:
            text = f"✅ {spec_name}"
        else:
            text = spec_name
        builder.add(InlineKeyboardButton(text=text, callback_data=f"reg_multi_spec:{spec_id}"))
    
    builder.adjust(2)
    
    # Add confirm button if at least one selected
    if selected_ids:
        builder.row(InlineKeyboardButton(text="✓ تأكيد الاختيار", callback_data="reg_spec_confirm"))
    
    return builder.as_markup()


def get_subjects_keyboard(subjects: list[tuple[int, str]], selected_ids: list[int] = None) -> InlineKeyboardMarkup:
    """Get subjects selection keyboard for teachers (multiple selection)."""
    selected_ids = selected_ids or []
    builder = InlineKeyboardBuilder()
    
    for subject_id, subject_name in subjects:
        if subject_id in selected_ids:
            text = f"✅ {subject_name}"
        else:
            text = subject_name
        builder.add(InlineKeyboardButton(text=text, callback_data=f"reg_subject:{subject_id}"))
    
    builder.adjust(2)
    
    # Add confirm and skip buttons
    row_buttons = []
    if selected_ids:
        row_buttons.append(InlineKeyboardButton(text="✓ تأكيد الاختيار", callback_data="reg_subjects_confirm"))
    row_buttons.append(InlineKeyboardButton(text="تخطي", callback_data="reg_subjects_skip"))
    builder.row(*row_buttons)
    
    return builder.as_markup()


def get_social_media_keyboard() -> InlineKeyboardMarkup:
    """Get social media links keyboard."""
    builder = InlineKeyboardBuilder()
    
    # LinkedIn
    builder.add(InlineKeyboardButton(
        text="💼 LinkedIn",
        url="https://www.linkedin.com/company/damascus-training-center-dtc"
    ))
    
    # Facebook
    builder.add(InlineKeyboardButton(
        text="📘 Facebook",
        url="https://www.facebook.com/DTC.UNRWA/"
    ))
    
    # UNRWA Official
    builder.add(InlineKeyboardButton(
        text="🌐 UNRWA Official",
        url="https://www.unrwa.org/newsroom/features/empowering-futures-unrwa%E2%80%99s-damascus-training-centre-links-skills-opportunity"
    ))
    
    builder.adjust(2, 1)  # First row: 2 buttons, Second row: 1 button
    
    return builder.as_markup()


def get_teacher_panel_keyboard() -> ReplyKeyboardMarkup:
    """Get teacher control panel keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📤 رفع محاضرات"))
    builder.add(KeyboardButton(text="📝 رفع وظائف"))
    builder.add(KeyboardButton(text="📥 تنزيل وظائف الطلاب"))
    builder.add(KeyboardButton(text="🔙 العودة للقائمة الرئيسية"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_e_learning_keyboard() -> ReplyKeyboardMarkup:
    """Get e-learning menu keyboard for students."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📚 محاضرات"))
    builder.add(KeyboardButton(text="📝 وظائف"))
    builder.add(KeyboardButton(text="🔙 العودة للقائمة الرئيسية"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)