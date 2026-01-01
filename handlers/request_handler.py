"""Service request handler."""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_request_offer_keyboard, get_specialization_keyboard_with_ids, get_accept_reject_keyboard, get_jobs_menu_keyboard
from handlers.common import require_auth
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, ServiceRequest, RequestStatus, ContactRequest, ContactRequestStatus, Gender
from services.request_service import RequestService
from repositories.request_repository import ServiceRequestRepository
from repositories.contact_repository import ContactRequestRepository
from repositories.specialization_repository import SpecializationRepository
from config import config

router = Router()


class RequestStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_specializations = State()
    waiting_for_preferred_gender = State()
    waiting_for_budget = State()


@router.message(F.text == "طلب خدمة")
@require_auth
async def start_request_service(message: Message, state: FSMContext, user: User):
    """Start request service flow."""
    await message.answer(
        "دعنا ننشئ طلب خدمتك!\n\n"
        "يرجى إدخال عنوان لطلبك:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(RequestStates.waiting_for_title)


@router.message(RequestStates.waiting_for_title)
async def process_request_title(message: Message, state: FSMContext, user: User):
    """Process request title."""
    if message.text == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إنشاء الطلب.", reply_markup=get_jobs_menu_keyboard())
        return
    
    if not message.text:
        await message.answer("❌ يرجى إدخال نص صحيح للعنوان.")
        return
    
    title = message.text.strip()
    
    if not title or len(title) < 5:
        await message.answer("❌ يجب أن يكون العنوان 5 أحرف على الأقل. يرجى المحاولة مرة أخرى:")
        return
    
    if len(title) > 200:
        await message.answer("❌ العنوان طويل جداً. الحد الأقصى 200 حرف. يرجى المحاولة مرة أخرى:")
        return
    
    await state.update_data(title=title)
    await message.answer("الآن يرجى إدخال وصف مفصل لما تحتاجه:")
    await state.set_state(RequestStates.waiting_for_description)


@router.message(RequestStates.waiting_for_description)
async def process_request_description(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Process request description."""
    if message.text == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إنشاء الطلب.", reply_markup=get_jobs_menu_keyboard())
        return
    
    if not message.text:
        await message.answer("❌ يرجى إدخال نص صحيح للوصف.")
        return
    
    description = message.text.strip()
    
    if not description or len(description) < 20:
        await message.answer("❌ يجب أن يكون الوصف 20 حرفاً على الأقل. يرجى المحاولة مرة أخرى:")
        return
    
    if len(description) > 3000:
        await message.answer("❌ الوصف طويل جداً. الحد الأقصى 3000 حرف. يرجى المحاولة مرة أخرى:")
        return
    
    await state.update_data(description=description)
    
    # Load specializations from database
    spec_repo = SpecializationRepository(db_session)
    specializations = await spec_repo.get_all_active()
    spec_list = [(spec.id, spec.name) for spec in specializations]
    
    if spec_list:
        await message.answer(
            "يرجى اختيار التخصصات المسموح لها بالرد على هذا الطلب.\n\n"
            "يمكنك اختيار عدة تخصصات:",
            reply_markup=get_specialization_keyboard_with_ids(spec_list)
        )
        await state.update_data(selected_specializations=[], specialization_names={})
        await state.set_state(RequestStates.waiting_for_specializations)
    else:
        await message.answer(
            "لا توجد اختصاصات متاحة حالياً. يرجى التواصل مع المشرف."
        )


@router.callback_query(F.data.startswith("select_spec_id:"), RequestStates.waiting_for_specializations)
async def process_specialization_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Process specialization selection."""
    spec_id = int(callback.data.split(":")[1])
    
    # Get specialization name from database
    spec_repo = SpecializationRepository(db_session)
    spec = await spec_repo.get_by_id(spec_id)
    
    if not spec:
        await callback.answer("التخصص غير موجود.", show_alert=True)
        return
    
    data = await state.get_data()
    selected_ids = data.get("selected_specializations", [])
    spec_names = data.get("specialization_names", {})
    
    if spec_id in selected_ids:
        selected_ids.remove(spec_id)
        if spec_id in spec_names:
            del spec_names[spec_id]
        await callback.answer(f"تم إزالة {spec.name}")
    else:
        selected_ids.append(spec_id)
        spec_names[spec_id] = spec.name
        await callback.answer(f"تم إضافة {spec.name}")
    
    await state.update_data(selected_specializations=selected_ids, specialization_names=spec_names)
    
    # Reload keyboard with all specializations
    all_specs = await spec_repo.get_all_active()
    spec_list = [(s.id, s.name) for s in all_specs]
    
    if selected_ids:
        selected_names = [spec_names.get(sid, "") for sid in selected_ids]
        await callback.message.edit_text(
            f"التخصصات المختارة: {', '.join(selected_names)}\n\n"
            "تابع الاختيار أو اضغط 'تم' عند الانتهاء:",
            reply_markup=get_specialization_keyboard_with_ids(spec_list)
        )
    else:
        await callback.message.edit_text(
            "يرجى اختيار تخصص واحد على الأقل:",
            reply_markup=get_specialization_keyboard_with_ids(spec_list)
        )


@router.message(RequestStates.waiting_for_specializations)
async def finish_specialization_selection(message: Message, state: FSMContext, db_session: AsyncSession, user: User, bot: Bot):
    """Finish specialization selection and ask for preferred gender."""
    if message.text == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إنشاء الطلب.", reply_markup=get_jobs_menu_keyboard())
        return
    
    if message.text and message.text.lower() in ["done", "تم"]:
        data = await state.get_data()
        selected_ids = data.get("selected_specializations", [])
        spec_names = data.get("specialization_names", {})
        
        if not selected_ids:
            await message.answer("يرجى اختيار تخصص واحد على الأقل قبل المتابعة.")
            return
        
        # Ask for preferred gender
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="ذكر", callback_data="select_gender:male"))
        keyboard.add(InlineKeyboardButton(text="أنثى", callback_data="select_gender:female"))
        keyboard.add(InlineKeyboardButton(text="لا يهم", callback_data="select_gender:any"))
        keyboard.adjust(3)
        
        await message.answer(
            "ما هو الجنس المفضل لمقدم الخدمة؟",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(RequestStates.waiting_for_preferred_gender)
    else:
        await message.answer("اضغط 'تم' عند الانتهاء من اختيار التخصصات، أو استخدم الأزرار أعلاه.")


@router.callback_query(F.data.startswith("select_gender:"), RequestStates.waiting_for_preferred_gender)
async def process_preferred_gender(callback: CallbackQuery, state: FSMContext):
    """Process preferred gender selection."""
    gender_str = callback.data.split(":")[1]
    
    gender_map = {
        "male": Gender.MALE,
        "female": Gender.FEMALE,
        "any": None
    }
    
    preferred_gender = gender_map.get(gender_str)
    await state.update_data(preferred_gender=preferred_gender)
    
    await callback.answer()
    await callback.message.edit_text(
        f"تم اختيار: {'ذكر' if gender_str == 'male' else 'أنثى' if gender_str == 'female' else 'لا يهم'}\n\n"
        "الآن يرجى إدخال ميزانيتك:\n\n"
        "يمكنك إدخال:\n"
        "- ميزانية ثابتة (مثلاً: 150 أو 150$)\n"
        "- نطاق ميزانية (مثلاً: 150-200 أو 150$-200$)",
        reply_markup=None
    )
    await state.set_state(RequestStates.waiting_for_budget)


@router.message(RequestStates.waiting_for_budget)
async def process_budget(message: Message, state: FSMContext, db_session: AsyncSession, user: User, bot: Bot):
    """Process budget and publish request."""
    if not message.text:
        await message.answer("❌ يرجى إدخال نص صحيح للميزانية.")
        return
    
    if message.text.strip() == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إنشاء الطلب.", reply_markup=get_jobs_menu_keyboard())
        return
    
    budget_str = message.text.strip()
    
    if not budget_str:
        await message.answer("❌ يرجى إدخال قيمة للميزانية (مثال: 150 أو 150-200).")
        return
    
    data = await state.get_data()
    
    # التحقق من وجود البيانات المطلوبة
    if "title" not in data or "description" not in data:
        await message.answer("❌ حدث خطأ في البيانات. يرجى البدء من جديد.")
        await state.clear()
        return
    
    # Get specialization names from IDs
    selected_ids = data.get("selected_specializations", [])
    spec_names = data.get("specialization_names", {})
    selected_spec_names = [spec_names.get(sid, "") for sid in selected_ids if sid in spec_names]
    
    if not selected_spec_names:
        await message.answer("❌ يرجى اختيار تخصص واحد على الأقل.")
        await state.set_state(RequestStates.waiting_for_specializations)
        return
    
    request_service = RequestService(db_session)
    
    try:
        success, request, error = await request_service.create_request(
            user,
            data["title"],
            data["description"],
            selected_spec_names,
            budget_str,
            data.get("preferred_gender")
        )
        
        if not success:
            error_message = error or "حدث خطأ غير معروف"
            await message.answer(f"❌ {error_message}\n\nيرجى المحاولة مرة أخرى:")
            return  # لا نمسح الـ state حتى يتمكن المستخدم من إعادة إدخال الميزانية
    except Exception as e:
        await message.answer(f"❌ حدث خطأ أثناء إنشاء الطلب: {str(e)}\n\nيرجى المحاولة مرة أخرى.")
        return
    
    request.status = RequestStatus.PENDING.value  # type: ignore
    request_repo = ServiceRequestRepository(db_session)
    request = await request_repo.update(request)
    
    # Send to admin group for approval
    try:
        request_text = f"🆕 طلب خدمة جديد يحتاج للموافقة\n\n"
        request_text += f"📌 العنوان: {request.title}\n\n"
        request_text += f"📝 الوصف: {request.description}\n\n"
        request_text += f"🎓 التخصصات المطلوبة: {', '.join(request.allowed_specializations)}\n"
        if request.preferred_gender:
            gender_names = {"male": "ذكر", "female": "أنثى"}
            gender_text = gender_names.get(str(request.preferred_gender), str(request.preferred_gender))
            request_text += f"⚧️ الجنس المفضل: {gender_text}\n"
        request_text += f"💰 الميزانية: {request_service.format_budget(request)}\n"
        request_text += f"👤 طالب الخدمة: {user.full_name or 'غير معروف'}\n"
        request_text += f"📧 البريد: {user.email}\n"
        if user.phone_number:
            request_text += f"📱 الهاتف: {user.phone_number}\n"
        request_text += f"\n🆔 رقم الطلب: {request.id}"
        
        request_id: int = request.id  # type: ignore[assignment]
        from handlers.keyboards import get_admin_approval_keyboard
        keyboard = get_admin_approval_keyboard(request_id, "request")
        
        sent_message = await bot.send_message(
            config.ADMIN_GROUP_ID,
            request_text,
            reply_markup=keyboard
        )
        
        request.channel_message_id = sent_message.message_id
        await request_repo.update(request)
        
        await message.answer(
            "✅ تم إرسال طلب خدمتك للموافقة!\n"
            "سيتم مراجعته من قبل المشرفين ونشره بعد الموافقة.",
            reply_markup=get_jobs_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"تم إنشاء الطلب لكن فشل إرساله للموافقة: {e}")
        request.status = RequestStatus.DRAFT.value  # type: ignore
        await request_repo.update(request)
    
    await state.clear()


@router.callback_query(F.data.startswith("offer_service:"))
@require_auth
async def offer_service(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot):
    """Handle offer to provide a requested service."""
    request_id = int(callback.data.split(":")[1])
    
    request_repo = ServiceRequestRepository(db_session)
    request = await request_repo.get_by_id(request_id)
    
    if not request:
        await callback.answer("الطلب غير موجود.", show_alert=True)
        return
    
    user_id: int = user.id  # type: ignore[assignment]
    if request.requester_id == user_id:
        await callback.answer("لا يمكنك الرد على طلبك الخاص.", show_alert=True)
        return
    
    request_service = RequestService(db_session)
    can_respond, error = request_service.can_respond_to_request(user, request)
    
    if not can_respond:
        await callback.answer(error, show_alert=True)
        return
    
    # Create contact request (provider offering to requester)
    contact_repo = ContactRequestRepository(db_session)
    
    # Check if already offered
    existing = await contact_repo.get_by_user(user_id)
    for contact in existing:
        if contact.service_request_id == request_id and contact.provider_id == user_id:
            await callback.answer("لقد عرضت تقديم هذه الخدمة بالفعل.", show_alert=True)
            return
    
    requester_id: int = request.requester_id  # type: ignore[assignment]
    contact_request = ContactRequest(
        requester_id=requester_id,
        provider_id=user_id,
        service_request_id=request_id,
        status=ContactRequestStatus.PENDING.value  # type: ignore
    )
    contact_request = await contact_repo.create(contact_request)
    
    # Notify requester (طالب الخدمة - العميل)
    requester = request.requester
    notification_text = f"📬 عرض خدمة جديد\n\n"
    notification_text += f"الطلب: {request.title}\n\n"
    notification_text += f"🎓 طالب (مقدم الخدمة):\n"
    notification_text += f"الاسم: {user.full_name or 'غير معروف'}\n"
    notification_text += f"التخصص: {user.specialization or 'غير محدد'}\n"
    
    # عرض رقم الطالب إذا كان متاحاً
    student_id = getattr(user, 'student_id', None)
    if student_id:
        notification_text += f"رقم الطالب: {student_id}\n"
    
    notification_text += f"البريد الإلكتروني: {user.email}\n"
    if user.phone_number:
        notification_text += f"الهاتف: {user.phone_number}\n"
    
    try:
        await bot.send_message(
            requester.telegram_id,
            notification_text,
            reply_markup=get_accept_reject_keyboard(contact_request.id)
        )
    except Exception:
        pass
    
    await callback.answer("✅ تم إرسال عرضك! سيتم إشعار صاحب الطلب.")


@router.callback_query(F.data.startswith("accept_contact:"))
@require_auth
async def accept_request_contact(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot):
    """Handle contact request acceptance for service requests."""
    contact_id = int(callback.data.split(":")[1])
    
    contact_repo = ContactRequestRepository(db_session)
    contact = await contact_repo.get_by_id(contact_id)
    
    user_id: int = user.id  # type: ignore[assignment]
    if not contact or contact.requester_id != user_id:
        await callback.answer("طلب غير صحيح.", show_alert=True)
        return
    
    if contact.status != ContactRequestStatus.PENDING:
        await callback.answer("تم معالجة هذا الطلب بالفعل.", show_alert=True)
        return
    
    contact.status = ContactRequestStatus.ACCEPTED.value  # type: ignore
    await contact_repo.update(contact)
    
    # Send contact info
    requester = contact.requester
    provider = contact.provider
    
    # requester هو طالب الخدمة (العميل الذي يطلب الخدمة)
    # provider هو الطالب الذي قدم عرضاً لتنفيذ الخدمة
    requester_text = f"✅ تم قبول طلب التواصل!\n\n"
    requester_text += f"الطلب: {contact.service_request.title if contact.service_request else 'غير متاح'}\n\n"
    requester_text += f"🎓 معلومات الطالب (مقدم الخدمة):\n"
    requester_text += f"الاسم: {provider.full_name or 'غير متاح'}\n"
    
    # عرض رقم الطالب والتخصص
    provider_student_id = getattr(provider, 'student_id', None)
    provider_specialization = getattr(provider, 'specialization', None)
    if provider_student_id:
        requester_text += f"رقم الطالب: {provider_student_id}\n"
    if provider_specialization:
        requester_text += f"التخصص: {provider_specialization}\n"
    
    requester_text += f"البريد الإلكتروني: {provider.email}\n"
    if provider.phone_number:
        requester_text += f"الهاتف: {provider.phone_number}\n"
    
    # رسالة للطالب (مقدم الخدمة)
    provider_text = f"✅ تم قبول عرضك!\n\n"
    provider_text += f"الطلب: {contact.service_request.title if contact.service_request else 'غير متاح'}\n\n"
    provider_text += f"👤 معلومات العميل (طالب الخدمة):\n"
    provider_text += f"الاسم: {requester.full_name or 'غير متاح'}\n"
    provider_text += f"البريد الإلكتروني: {requester.email}\n"
    if requester.phone_number:
        provider_text += f"الهاتف: {requester.phone_number}\n"
    
    try:
        await bot.send_message(requester.telegram_id, requester_text)
        await bot.send_message(provider.telegram_id, provider_text)
    except Exception:
        pass
    
    # Delete request message from channel
    if contact.service_request and contact.service_request.channel_message_id:
        try:
            await bot.delete_message(config.REQUESTS_CHANNEL_ID, contact.service_request.channel_message_id)
            contact.service_request.status = RequestStatus.CONTACT_ACCEPTED.value  # type: ignore
            request_repo = ServiceRequestRepository(db_session)
            await request_repo.update(contact.service_request)
        except Exception:
            pass
    
    await callback.answer("تم قبول طلب التواصل!", show_alert=True)
    await callback.message.edit_text("✅ تم قبول طلب التواصل. تم مشاركة معلومات الاتصال.")


@router.callback_query(F.data.startswith("reject_contact:"))
@require_auth
async def reject_request_contact(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot):
    """Handle contact request rejection for service requests."""
    contact_id = int(callback.data.split(":")[1])
    
    contact_repo = ContactRequestRepository(db_session)
    contact = await contact_repo.get_by_id(contact_id)
    
    user_id: int = user.id  # type: ignore[assignment]
    if not contact or contact.requester_id != user_id:
        await callback.answer("طلب غير صحيح.", show_alert=True)
        return
    
    if contact.status != ContactRequestStatus.PENDING:
        await callback.answer("تم معالجة هذا الطلب بالفعل.", show_alert=True)
        return
    
    contact.status = ContactRequestStatus.REJECTED.value  # type: ignore
    await contact_repo.update(contact)
    
    # Notify provider
    provider = contact.provider
    try:
        await bot.send_message(
            provider.telegram_id,
            f"❌ تم رفض عرضك لطلب '{contact.service_request.title if contact.service_request else 'الطلب'}'."
        )
    except Exception:
        pass
    
    await callback.answer("تم رفض طلب التواصل.", show_alert=True)
    await callback.message.edit_text("❌ تم رفض طلب التواصل. تم إشعار مقدم الخدمة.")

