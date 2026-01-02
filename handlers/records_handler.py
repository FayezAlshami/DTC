"""Records handler (Your Records)."""
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from handlers.keyboards import get_main_menu_keyboard, get_jobs_menu_keyboard, get_social_media_keyboard, get_teacher_panel_keyboard
from handlers.common import require_auth, require_teacher
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, ServiceStatus, RequestStatus, ContactRequestStatus
from repositories.service_repository import ServiceRepository
from repositories.request_repository import ServiceRequestRepository
from repositories.contact_repository import ContactRequestRepository
from services.service_service import ServiceService
from services.request_service import RequestService
import os

router = Router()


@router.message(F.text == "💼 الوظائف")
@require_auth
async def show_jobs_menu(message: Message, user: User):
    """Show jobs submenu."""
    await message.answer(
        "💼 الوظائف\n\nاختر الخيار المطلوب:",
        reply_markup=get_jobs_menu_keyboard()
    )


@router.message(F.text == "🔙 العودة للقائمة الرئيسية")
@require_auth
async def back_to_main_menu(message: Message, user: User):
    """Return to main menu."""
    await message.answer(
        "القائمة الرئيسية",
        reply_markup=get_main_menu_keyboard(user.profile_completed, user.role.value, bool(user.is_student))
    )


@router.message(F.text == "📱 التواصل الاجتماعي")
@require_auth
async def show_social_media(message: Message, user: User):
    """Show DTC social media accounts with logo."""
    
    # Creative Arabic message
    social_message = """

     🏛️ مركز دمشق للتدريب - DTC      


🌟 <b>تمكين المستقبل منذ عام 1961</b> 🌟

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 <i>مركز دمشق للتدريب (DTC) هو مؤسسة تعليمية
تابعة للأونروا، تأسس لتوفير التعليم التقني
والمهني المجاني للاجئين الفلسطينيين.</i>

🎓 <b>أكثر من 15,430 خريج</b> حتى الآن!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 <b>تواصل معنا عبر:</b>

💼 <b>LinkedIn</b> - شبكتنا المهنية
📘 <b>Facebook</b> - مجتمعنا الاجتماعي  
🌐 <b>UNRWA</b> - موقعنا الرسمي

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>🤝 انضم إلينا وكن جزءاً من قصة النجاح!</i>
"""

    # Get the logo path
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "logo.png")
    
    # Check if logo exists
    if os.path.exists(logo_path):
        # Send photo with caption
        photo = FSInputFile(logo_path)
        await message.answer_photo(
            photo=photo,
            caption=social_message,
            parse_mode="HTML",
            reply_markup=get_social_media_keyboard()
        )
    else:
        # Fallback: send just the message
        await message.answer(
            social_message,
            parse_mode="HTML",
            reply_markup=get_social_media_keyboard()
        )


@router.message(F.text == "👨‍🏫 لوحة الأستاذ")
@require_auth
@require_teacher
async def show_teacher_panel(message: Message, user: User):
    """Show teacher control panel with options."""
    panel_message = f"""
👨‍🏫 <b>لوحة الأستاذ</b>

مرحباً بك، {user.full_name or 'الأستاذ'}!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>اختر الإجراء المطلوب:</b>

📤 <b>رفع محاضرات</b> - رفع محاضرات جديدة للطلاب
📝 <b>رفع وظائف</b> - رفع وظائف وواجبات للطلاب
📥 <b>تنزيل وظائف الطلاب</b> - عرض وتنزيل الوظائف المقدمة من الطلاب

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await message.answer(
        panel_message,
        parse_mode="HTML",
        reply_markup=get_teacher_panel_keyboard()
    )


@router.message(F.text == "سجلاتك")
@require_auth
async def show_records(message: Message, db_session: AsyncSession, user: User):
    """Show user's records."""
    records_text = "📊 سجلاتك\n\n"
    
    # Services provided
    service_repo = ServiceRepository(db_session)
    user_id: int = user.id  # type: ignore[assignment]
    services = await service_repo.get_by_provider(user_id)
    
    if services:
        records_text += f"📤 الخدمات المقدمة ({len(services)}):\n"
        service_service = ServiceService(db_session)
        for service in services[:10]:  # Show first 10
            status_emoji = {
                ServiceStatus.DRAFT: "📝",
                ServiceStatus.PUBLISHED: "✅",
                ServiceStatus.REMOVED: "❌",
                ServiceStatus.COMPLETED: "✔️",
                ServiceStatus.CONTACT_ACCEPTED: "🤝",
                ServiceStatus.EXPIRED: "⏰"
            }
            records_text += f"{status_emoji.get(service.status, '📌')} {service.title} - {service.status.value}\n"
            records_text += f"   السعر: {service_service.format_price(service)}\n"
        if len(services) > 10:
            records_text += f"... و {len(services) - 10} المزيد\n"
        records_text += "\n"
    
    # Service requests
    request_repo = ServiceRequestRepository(db_session)
    requests = await request_repo.get_by_requester(user_id)
    
    if requests:
        records_text += f"📥 طلبات الخدمات ({len(requests)}):\n"
        request_service = RequestService(db_session)
        for req in requests[:10]:  # Show first 10
            status_emoji = {
                RequestStatus.DRAFT: "📝",
                RequestStatus.PUBLISHED: "✅",
                RequestStatus.REMOVED: "❌",
                RequestStatus.COMPLETED: "✔️",
                RequestStatus.CONTACT_ACCEPTED: "🤝",
                RequestStatus.EXPIRED: "⏰"
            }
            records_text += f"{status_emoji.get(req.status, '📌')} {req.title} - {req.status.value}\n"
            records_text += f"   الميزانية: {request_service.format_budget(req)}\n"
        if len(requests) > 10:
            records_text += f"... و {len(requests) - 10} المزيد\n"
        records_text += "\n"
    
    # Contact requests
    contact_repo = ContactRequestRepository(db_session)
    contacts = await contact_repo.get_by_user(user_id)
    
    if contacts:
        sent_contacts = [c for c in contacts if c.requester_id == user_id]
        received_contacts = [c for c in contacts if c.provider_id == user_id]
        
        if sent_contacts:
            records_text += f"📤 طلبات التواصل المرسلة ({len(sent_contacts)}):\n"
            for contact in sent_contacts[:5]:
                status_emoji = {
                    ContactRequestStatus.PENDING: "⏳",
                    ContactRequestStatus.ACCEPTED: "✅",
                    ContactRequestStatus.REJECTED: "❌"
                }
                service_name = contact.service.title if contact.service else (contact.service_request.title if contact.service_request else "غير متاح")
                records_text += f"{status_emoji.get(contact.status, '📌')} {service_name} - {contact.status.value}\n"
            if len(sent_contacts) > 5:
                records_text += f"... و {len(sent_contacts) - 5} المزيد\n"
            records_text += "\n"
        
        if received_contacts:
            records_text += f"📥 طلبات التواصل المستلمة ({len(received_contacts)}):\n"
            for contact in received_contacts[:5]:
                status_emoji = {
                    ContactRequestStatus.PENDING: "⏳",
                    ContactRequestStatus.ACCEPTED: "✅",
                    ContactRequestStatus.REJECTED: "❌"
                }
                service_name = contact.service.title if contact.service else (contact.service_request.title if contact.service_request else "غير متاح")
                requester_name = contact.requester.full_name or "غير معروف"
                records_text += f"{status_emoji.get(contact.status, '📌')} {service_name} من {requester_name} - {contact.status.value}\n"
            if len(received_contacts) > 5:
                records_text += f"... و {len(received_contacts) - 5} المزيد\n"
            records_text += "\n"
    
    if not services and not requests and not contacts:
        records_text += "لم يتم العثور على سجلات. ابدأ بتقديم خدمة أو تقديم طلب!"
    
    await message.answer(records_text, reply_markup=get_jobs_menu_keyboard())

