"""Service handler (Provide a Service)."""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_service_contact_keyboard, get_accept_reject_keyboard, get_jobs_menu_keyboard
from handlers.common import require_auth, require_student
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Service, ServiceStatus, ContactRequest, ContactRequestStatus
from services.service_service import ServiceService
from services.profile_service import ProfileService
from repositories.service_repository import ServiceRepository
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.types import Message as TelegramMessage  # أضيف هاد السطر

from repositories.contact_repository import ContactRequestRepository
from config import config


router = Router()


class ServiceStates(StatesGroup):
    waiting_for_media = State()
    waiting_for_title_description = State()
    waiting_for_price = State()


@router.message(F.text == "تقديم خدمة")
@require_auth
async def start_provide_service(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Start provide service flow."""
    profile_service = ProfileService(db_session)
    can_provide, error = profile_service.can_provide_service(user)
    
    if not can_provide:
        await message.answer(
            f"❌ {error}\n\n"
            "يرجى إكمال ملفك الشخصي أولاً، بما في ذلك رقم الطالب والتخصص."
        )
        return
    
    await message.answer(
        "دعنا ننشئ قائمة خدمتك!\n\n"
        "أولاً، يمكنك إرسال صورة أو فيديو لخدمتك (اختياري).\n"
        "أو اكتب 'تخطي' للمتابعة بدون وسائط:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ServiceStates.waiting_for_media)


@router.message(ServiceStates.waiting_for_media)
async def process_media(message: Message, state: FSMContext, user: User, **kwargs):
    """Process media or skip."""
    if message.text == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إنشاء الخدمة.", reply_markup=get_jobs_menu_keyboard())
        return
    
    media_file_id = None
    media_type = None
    
    if message.text and message.text.lower() not in ["skip", "تخطي"]:
        await message.answer("يرجى إرسال صورة أو فيديو، أو اكتب 'تخطي':")
        return
    
    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.text and message.text.lower() in ["skip", "تخطي"]:
        pass
    else:
        await message.answer("يرجى إرسال صورة أو فيديو، أو اكتب 'تخطي':")
        return
    
    await state.update_data(media_file_id=media_file_id, media_type=media_type)
    await message.answer(
        "الآن يرجى إرسال عنوان الخدمة والوصف بهذه الصيغة:\n\n"
        "السطر الأول: العنوان (مطلوب)\n"
        "السطر الثاني وما بعده: الوصف (مطلوب)\n\n"
        "مثال:\n"
        "خدمات تطوير الويب\n"
        "أقدم خدمات تطوير الويب الاحترافية بما في ذلك تطوير الواجهات الأمامية والخلفية، تصميم قواعد البيانات، والنشر."
    )
    await state.set_state(ServiceStates.waiting_for_title_description)


@router.message(ServiceStates.waiting_for_title_description)
async def process_title_description(message: Message, state: FSMContext, db_session: AsyncSession, user: User, **kwargs):
    """Process title and description."""
    if not message.text:
        await message.answer("يرجى إرسال نص صحيح.")
        return
    
    if message.text == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إنشاء الخدمة.", reply_markup=get_jobs_menu_keyboard())
        return
    
    lines = message.text.strip().split("\n", 1)
    if len(lines) < 2:
        await message.answer("يرجى تقديم العنوان (السطر الأول) والوصف (الأسطر المتبقية):")
        return
    
    title = lines[0].strip()
    description = lines[1].strip()
    
    # التحقق من الطول
    if len(title) < 5:
        await message.answer("العنوان يجب أن يكون على الأقل 5 أحرف. يرجى المحاولة مرة أخرى:")
        return
    
    if len(description) < 20:
        await message.answer("الوصف يجب أن يكون على الأقل 20 حرف. يرجى المحاولة مرة أخرى:")
        return
    
    # حفظ البيانات في الـ state
    await state.update_data(title=title, description=description)
    
    await message.answer(
        "الآن يرجى إدخال سعر الخدمة:\n\n"
        "يمكنك إدخال:\n"
        "- سعر ثابت (مثلاً: 200 أو 200$)\n"
        "- نطاق سعر (مثلاً: 200-300 أو 200$-300$)"
    )
    await state.set_state(ServiceStates.waiting_for_price)


@router.message(ServiceStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext, db_session: AsyncSession, user: User, bot: Bot, **kwargs):
    """Process price and publish service."""
    if not message.text:
        await message.answer("يرجى إدخال نص صحيح.")
        return
    
    if message.text == "إلغاء":
        await state.clear()
        await message.answer("تم إلغاء إنشاء الخدمة.", reply_markup=get_jobs_menu_keyboard())
        return
    
    price_str = message.text.strip()
    
    # التحقق من صحة السعر
    service_service = ServiceService(db_session)
    is_valid, error, price_fixed, price_min, price_max = service_service.validate_price(price_str)
    
    if not is_valid:
        await message.answer(f"❌ {error}\n\nيرجى المحاولة مرة أخرى:")
        return
    
    # جلب البيانات من الـ state
    data = await state.get_data()
    title = data.get('title')
    description = data.get('description')
    media_file_id = data.get('media_file_id')
    media_type = data.get('media_type')
    
    # إنشاء الخدمة الآن مع السعر الصحيح
    success, service, error = await service_service.create_service(
        user,
        title,  # type: ignore
        description,  # type: ignore
        price_str,
        media_file_id,
        media_type
    )
    
    if not success:
        await message.answer(f"❌ خطأ: {error}")
        await state.clear()
        return
    
    # تحديث حالة الخدمة إلى في انتظار الموافقة
    service_repo = ServiceRepository(db_session)
    # Use .value to get the string value instead of enum name
    service.status = ServiceStatus.PENDING.value  # type: ignore
    service = await service_repo.update(service)
    
    # إرسال الطلب إلى مجموعة المشرفين للموافقة
    try:
        service_text = f"🆕 طلب خدمة جديد يحتاج للموافقة\n\n"
        service_text += f"🎯 العنوان: {service.title}\n\n"  # type: ignore
        service_text += f"📝 الوصف: {service.description}\n\n"  # type: ignore
        service_text += f"💰 السعر: {service_service.format_price(service)}\n"
        service_text += f"🎓 التخصص: {service.specialization}\n"  # type: ignore
        user_full_name = getattr(user, 'full_name', None)
        service_text += f"👤 الطالب: {user_full_name if user_full_name not in [None, ''] else 'غير معروف'}\n"
        service_text += f"📧 البريد: {user.email}\n"
        phone_number = getattr(user, 'phone_number', None)
        if phone_number and phone_number not in [None, '']:
            service_text += f"📱 الهاتف: {phone_number}\n"
        service_text += f"\n🆔 رقم الطلب: {service.id}"  # type: ignore
        
        service_id: int = service.id  # type: ignore
        from handlers.keyboards import get_admin_approval_keyboard
        keyboard = get_admin_approval_keyboard(service_id, "service")
        
        if service.media_file_id:  # type: ignore
            if str(service.media_type) == "photo":  # type: ignore
                sent_message = await bot.send_photo(
                    config.ADMIN_GROUP_ID,
                    service.media_file_id,  # type: ignore
                    caption=service_text,
                    reply_markup=keyboard
                )
            else:  # video
                sent_message = await bot.send_video(
                    config.ADMIN_GROUP_ID,
                    service.media_file_id,  # type: ignore
                    caption=service_text,
                    reply_markup=keyboard
                )
        else:
            sent_message = await bot.send_message(
                config.ADMIN_GROUP_ID,
                service_text,
                reply_markup=keyboard
            )
        
        service.channel_message_id = sent_message.message_id  # type: ignore
        await service_repo.update(service)
        
        await message.answer(
            "✅ تم إرسال طلب خدمتك للموافقة!\n"
            "سيتم مراجعته من قبل المشرفين ونشره بعد الموافقة.",
            reply_markup=get_jobs_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"تم إنشاء الخدمة لكن فشل إرسالها للموافقة: {e}")
        service.status = ServiceStatus.DRAFT.value  # type: ignore
        await service_repo.update(service)
    
    await state.clear()


@router.callback_query(F.data.startswith("request_service_contact:"))
@require_auth
async def request_service_contact(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot, **kwargs):
    """Handle contact request for a service."""
    if not callback.data:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return
    
    service_id = int(callback.data.split(":")[1])
    
    service_repo = ServiceRepository(db_session)
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("الخدمة غير موجودة.", show_alert=True)
        return
    
    user_id: int = user.id  # type: ignore
    service_provider_id: int = service.provider_id  # type: ignore
    
    if service_provider_id == user_id:
        await callback.answer("لا يمكنك طلب التواصل لخدمتك الخاصة.", show_alert=True)
        return
    
    # Check if already requested or rejected
    contact_repo = ContactRequestRepository(db_session)
    existing = await contact_repo.get_by_user(user_id)
    for contact in existing:
        contact_service_id: int = contact.service_id  # type: ignore
        contact_status = str(contact.status) if contact.status else ""  # type: ignore
        if contact_service_id == service_id:
            if contact_status == str(ContactRequestStatus.PENDING):
                await callback.answer("لقد طلبت التواصل لهذه الخدمة بالفعل.", show_alert=True)
                return
            elif contact_status == str(ContactRequestStatus.REJECTED):
                await callback.answer("❌ لا يمكنك إرسال طلب تواصل جديد لهذه الخدمة. تم رفض طلبك السابق.", show_alert=True)
                return
    
    # Create contact request
    contact_request = ContactRequest(
        requester_id=user_id,
        provider_id=service_provider_id,
        service_id=service_id,
        status=ContactRequestStatus.PENDING.value  # type: ignore
    )
    contact_request = await contact_repo.create(contact_request)
    
    # Notify provider
    provider = service.provider  # type: ignore
    notification_text = f"📬 طلب تواصل جديد\n\n"
    notification_text += f"الخدمة: {service.title}\n"  # type: ignore
    notification_text += f"الطالب: {user.full_name or 'غير معروف'}\n"  # type: ignore
    notification_text += f"البريد الإلكتروني: {user.email}\n"  # type: ignore
    
    user_phone: str = user.phone_number  # type: ignore
    if user_phone:
        notification_text += f"الهاتف: {user_phone}\n"
    
    try:
        contact_request_id: int = contact_request.id  # type: ignore
        provider_telegram_id: int = provider.telegram_id  # type: ignore
        await bot.send_message(
            provider_telegram_id,
            notification_text,
            reply_markup=get_accept_reject_keyboard(contact_request_id)
        )
    except Exception:
        pass  # Provider might have blocked the bot
    
    await callback.answer("تم إرسال طلب التواصل! سيتم إشعار مقدم الخدمة.")


@router.callback_query(F.data.startswith("accept_contact:"))
@require_auth
async def accept_contact(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot, **kwargs):
    """Handle contact request acceptance."""
    if not callback.data:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return
    
    contact_id = int(callback.data.split(":")[1])
    
    contact_repo = ContactRequestRepository(db_session)
    contact = await contact_repo.get_by_id(contact_id)
    
    user_id: int = user.id  # type: ignore
    
    if not contact:
        await callback.answer("طلب غير صحيح.", show_alert=True)
        return
    
    contact_provider_id: int = contact.provider_id  # type: ignore
    if contact_provider_id != user_id:
        await callback.answer("طلب غير صحيح.", show_alert=True)
        return
    
    contact_status = str(contact.status) if contact.status else ""  # type: ignore
    if contact_status != str(ContactRequestStatus.PENDING):
        await callback.answer("تم معالجة هذا الطلب بالفعل.", show_alert=True)
        return
    
    contact.status = ContactRequestStatus.ACCEPTED.value  # type: ignore
    await contact_repo.update(contact)
    
    # Send contact info to requester
    requester = contact.requester  # type: ignore
    provider = contact.provider  # type: ignore
    
    requester_text = f"✅ تم قبول طلب التواصل!\n\n"
    requester_text += f"الخدمة: {contact.service.title if contact.service else 'غير متاح'}\n\n"  # type: ignore
    requester_text += f"معلومات الاتصال بمقدم الخدمة:\n"
    requester_text += f"الاسم: {provider.full_name or 'غير متاح'}\n"  # type: ignore
    requester_text += f"البريد الإلكتروني: {provider.email}\n"  # type: ignore
    
    provider_phone: str = provider.phone_number  # type: ignore
    if provider_phone:
        requester_text += f"الهاتف: {provider_phone}\n"
    
    provider_text = f"✅ لقد قبلت طلب التواصل.\n\n"
    provider_text += f"معلومات الاتصال بالطالب:\n"
    provider_text += f"الاسم: {requester.full_name or 'غير متاح'}\n"  # type: ignore
    provider_text += f"البريد الإلكتروني: {requester.email}\n"  # type: ignore
    
    requester_phone: str = requester.phone_number  # type: ignore
    if requester_phone:
        provider_text += f"الهاتف: {requester_phone}\n"
    
    try:
        requester_telegram_id: int = requester.telegram_id  # type: ignore
        provider_telegram_id: int = provider.telegram_id  # type: ignore
        await bot.send_message(requester_telegram_id, requester_text)
        await bot.send_message(provider_telegram_id, provider_text)
    except Exception:
        pass
    
    # Delete service message from channel if service exists
    if contact.service and contact.service.channel_message_id:  # type: ignore
        try:
            channel_message_id: int = contact.service.channel_message_id  # type: ignore
            await bot.delete_message(config.SERVICES_CHANNEL_ID, channel_message_id)
            contact.service.status = ServiceStatus.CONTACT_ACCEPTED.value  # type: ignore
            service_repo = ServiceRepository(db_session)
            await service_repo.update(contact.service)  # type: ignore
        except Exception:
            pass
    
    await callback.answer("تم قبول طلب التواصل!", show_alert=True)
    if callback.message and isinstance(callback.message, TelegramMessage):
        await callback.message.edit_text("✅ تم قبول طلب التواصل. تم مشاركة معلومات الاتصال.")


@router.callback_query(F.data.startswith("reject_contact:"))
@require_auth
async def reject_contact(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot, **kwargs):
    """Handle contact request rejection."""
    if not callback.data:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return
    
    contact_id = int(callback.data.split(":")[1])
    
    contact_repo = ContactRequestRepository(db_session)
    contact = await contact_repo.get_by_id(contact_id)
    
    user_id: int = user.id  # type: ignore
    
    if not contact:
        await callback.answer("طلب غير صحيح.", show_alert=True)
        return
    
    contact_provider_id: int = contact.provider_id  # type: ignore
    if contact_provider_id != user_id:
        await callback.answer("طلب غير صحيح.", show_alert=True)
        return
    
    contact_status = str(contact.status) if contact.status else ""  # type: ignore
    if contact_status != str(ContactRequestStatus.PENDING):
        await callback.answer("تم معالجة هذا الطلب بالفعل.", show_alert=True)
        return
    
    contact.status = ContactRequestStatus.REJECTED.value  # type: ignore
    await contact_repo.update(contact)
    
    # Notify requester
    requester = contact.requester  # type: ignore
    try:
        requester_telegram_id: int = requester.telegram_id  # type: ignore
        service_title = contact.service.title if contact.service else 'الخدمة'  # type: ignore
        await bot.send_message(
            requester_telegram_id,
            f"❌ تم رفض طلب التواصل الخاص بك لخدمة '{service_title}' من قبل مقدم الخدمة."
        )
    except Exception:
        pass
    
    await callback.answer("تم رفض طلب التواصل.", show_alert=True)
    if callback.message and isinstance(callback.message, TelegramMessage):
        await callback.message.edit_text("❌ تم رفض طلب التواصل. تم إشعار الطالب.")
