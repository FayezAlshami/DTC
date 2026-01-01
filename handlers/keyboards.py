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


def get_main_menu_keyboard(profile_completed: bool = False) -> ReplyKeyboardMarkup:
    """Get main menu keyboard."""
    builder = ReplyKeyboardBuilder()
    
    builder.add(KeyboardButton(text="💼 الوظائف"))
    builder.add(KeyboardButton(text="🎓 التعلّم الإلكتروني"))
    builder.add(KeyboardButton(text="📱 التواصل الاجتماعي"))
    builder.add(KeyboardButton(text="🕘 السجل"))
    builder.add(KeyboardButton(text="⚙️ الإعدادات"))
    
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
    """Get profile view keyboard with contact accounts button."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="➕ إضافة حسابات تواصل",
        callback_data="add_contact_accounts"
    ))
    if has_contact_accounts:
        builder.add(InlineKeyboardButton(
            text="📱 إدارة حسابات التواصل",
            callback_data="manage_contact_accounts"
        ))
    builder.adjust(1)
    return builder.as_markup()


def get_verification_retry_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard for verification code retry options."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="إعادة إرسال"))
    builder.add(KeyboardButton(text="إعادة إدخال عنوان البريد الإلكتروني"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)