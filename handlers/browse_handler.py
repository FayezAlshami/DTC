"""Browse services handler."""
from decimal import Decimal
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import (
    get_main_menu_keyboard,
    get_cancel_keyboard,
    get_specialization_keyboard,
    get_service_contact_keyboard,
    get_pagination_keyboard
)
from handlers.common import require_auth
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, ServiceStatus
from repositories.service_repository import ServiceRepository
from services.service_service import ServiceService


router = Router()


COMMON_SPECIALIZATIONS = [
    "Computer Science", "Information Technology", "Software Engineering",
    "Mathematics", "Physics", "Chemistry", "Biology",
    "Business Administration", "Economics", "Finance",
    "Engineering", "Mechanical Engineering", "Electrical Engineering",
    "Medicine", "Nursing", "Pharmacy",
    "Law", "Education", "Psychology"
]


SERVICES_PER_PAGE = 5


class BrowseStates(StatesGroup):
    waiting_for_specialization = State()
    waiting_for_price_filter = State()


@router.message(F.text == "تصفح الخدمات")
@require_auth
async def start_browse(message: Message, state: FSMContext):
    """Start browse services flow."""
    await message.answer(
        "دعنا نجد الخدمات المناسبة لك!\n\n"
        "يرجى اختيار تخصص للتصفية:",
        reply_markup=get_specialization_keyboard(COMMON_SPECIALIZATIONS)
    )
    await state.set_state(BrowseStates.waiting_for_specialization)


@router.callback_query(F.data.startswith("select_spec:"), BrowseStates.waiting_for_specialization)
async def process_specialization(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Process specialization selection."""
    # Handle None case for callback.data
    if not callback.data:
        await callback.answer("خطأ في البيانات")
        return
    
    spec = callback.data.split(":")[1]
    await state.update_data(specialization=spec)
    await callback.answer(f"تم الاختيار: {spec}")
    
    # ✅ استخدام isinstance بدل if not callback.message
    if not isinstance(callback.message, Message):
        return
    
    await callback.message.edit_text(
        f"التخصص المختار: {spec}\n\n"
        "الآن يرجى إدخال فلتر السعر:\n"
        "- الحد الأقصى للسعر (مثلاً: 500 أو 500$)\n"
        "- نطاق السعر (مثلاً: 100-500 أو 100$-500$)\n"
        "- اكتب 'الكل' لعرض جميع الأسعار"
    )
    await state.set_state(BrowseStates.waiting_for_price_filter)


@router.message(BrowseStates.waiting_for_price_filter)
async def process_price_filter(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Process price filter and show results."""
    # Handle None case for message.text
    if not message.text:
        await message.answer("يرجى إدخال نص صالح")
        return
    
    if message.text == "إلغاء":
        await state.clear()
        # Convert Column[bool] to bool
        await message.answer(
            "تم إلغاء التصفح.",
            reply_markup=get_main_menu_keyboard(bool(user.profile_completed))
        )
        return
    
    data = await state.get_data()
    specialization = data.get("specialization")
    
    price_filter = message.text.strip().lower()
    min_price = None
    max_price = None
    
    if price_filter not in ["all", "الكل"]:
        service_service = ServiceService(db_session)
        is_valid, error, price_fixed, price_min, price_max = service_service.validate_price(price_filter)
        
        if not is_valid:
            await message.answer(f"صيغة السعر غير صحيحة: {error}\n\nيرجى المحاولة مرة أخرى:")
            return
        
        if price_fixed:
            max_price = price_fixed
        else:
            min_price = price_min
            max_price = price_max
    
    # Fetch all matching services
    service_repo = ServiceRepository(db_session)
    services = await service_repo.get_published_services(
        specialization=specialization,
        min_price=min_price,
        max_price=max_price,
        skip=0,
        limit=1000
    )
    
    if not services:
        await message.answer(
            "لم يتم العثور على خدمات تطابق معاييرك.\n\n"
            "جرب فلاتر مختلفة أو تحقق لاحقاً.",
            reply_markup=get_main_menu_keyboard(bool(user.profile_completed))
        )
        await state.clear()
        return
    
    # Store services and pagination state
    await state.update_data(
        services=[s.id for s in services],
        page=1,
        specialization=specialization,
        min_price=min_price,
        max_price=max_price
    )
    
    await show_services_page(message, state, db_session, user)


async def show_services_page(
    message_or_callback,
    state: FSMContext,
    db_session: AsyncSession,
    user: User,
    page: int = 1
):
    """Show a page of services."""
    data = await state.get_data()
    service_ids = data.get("services", [])
    
    # Calculate pagination
    total_services = len(service_ids)
    total_pages = (total_services + SERVICES_PER_PAGE - 1) // SERVICES_PER_PAGE
    
    if page < 1 or page > total_pages:
        page = 1
    
    # Get services for this page
    start_idx = (page - 1) * SERVICES_PER_PAGE
    end_idx = start_idx + SERVICES_PER_PAGE
    page_service_ids = service_ids[start_idx:end_idx]
    
    service_repo = ServiceRepository(db_session)
    service_service = ServiceService(db_session)
    
    services_text = f"🔍 الخدمات الموجودة (الصفحة {page}/{total_pages})\n\n"
    
    # Add inline buttons for each service
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    
    for service_id in page_service_ids:
        service = await service_repo.get_by_id(service_id)
        if not service:
            continue
        
        services_text += f"📌 {service.title}\n"
        services_text += f"💰 {service_service.format_price(service)}\n"
        services_text += f"🎓 {service.specialization}\n"
        services_text += f"📝 {service.description[:100]}...\n\n"
        
        builder.add(InlineKeyboardButton(
            text=f"طلب التواصل - {service.title[:30]}",
            callback_data=f"request_service_contact:{service.id}"
        ))
    
    builder.adjust(1)
    
    # Add pagination if needed
    if total_pages > 1:
        pagination_kb = get_pagination_keyboard(page, total_pages, "browse", "")
        for row in pagination_kb.inline_keyboard:
            builder.row(*row)
    
    keyboard = builder.as_markup()
    
    # ✅ استخدام isinstance بشكل صحيح
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(
            services_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    elif isinstance(message_or_callback, CallbackQuery):
        # ✅ استخدام isinstance للتأكد من نوع Message
        if isinstance(message_or_callback.message, Message):
            await message_or_callback.message.edit_text(
                services_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    await state.update_data(page=page)


@router.callback_query(F.data.startswith("browse:page:"))
async def handle_browse_pagination(
    callback: CallbackQuery,
    state: FSMContext,
    db_session: AsyncSession,
    user: User
):
    """Handle browse pagination."""
    # Handle None case for callback.data
    if not callback.data:
        await callback.answer("خطأ في البيانات")
        return
    
    page = int(callback.data.split(":")[2])
    await show_services_page(callback, state, db_session, user, page)
    await callback.answer()
