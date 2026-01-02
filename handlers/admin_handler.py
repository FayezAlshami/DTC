"""Admin handler."""
from typing import cast, Sequence

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.types import Message as TelegramMessage

from handlers.keyboards import get_main_menu_keyboard, get_admin_menu_keyboard
from handlers.common import require_auth, require_admin
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UserRole, ServiceStatus, RequestStatus
from repositories.user_repository import UserRepository
from repositories.service_repository import ServiceRepository
from repositories.request_repository import ServiceRequestRepository
from repositories.admin_repository import AdminRepository
from config import config

router = Router()


def humanize_enum(enum_member) -> str:
    """Convert enum member to a human friendly label."""
    if enum_member is None:
        return "غير معروف"
    return enum_member.name.replace("_", " ").title()


@router.message(F.text == "/admin")
@require_auth
@require_admin
async def show_admin_menu(message: Message, user: User):
    """Show admin menu."""
    await message.answer(
        "🔧 لوحة الإدارة\n\n"
        "اختر خياراً:",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(F.text == "الإحصائيات")
@require_auth
@require_admin
async def show_statistics(message: Message, db_session: AsyncSession, user: User):
    """Show platform statistics."""
    admin_repo = AdminRepository(db_session)
    stats = await admin_repo.get_statistics()

    stats_text = "📊 إحصائيات المنصة\n\n"
    stats_text += f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
    stats_text += f"✅ المستخدمون النشطون: {stats['active_users']}\n"
    stats_text += f"🎓 المستخدمون الطلاب: {stats['student_users']}\n"
    stats_text += f"📤 إجمالي الخدمات: {stats['total_services']}\n"
    stats_text += f"📥 إجمالي الطلبات: {stats['total_requests']}\n"
    stats_text += f"🤝 الاتصالات المكتملة: {stats['completed_contacts']}\n"

    await message.answer(stats_text, reply_markup=get_admin_menu_keyboard())


@router.message(F.text == "إدارة الخدمات")
@require_auth
@require_admin
async def show_service_moderation(message: Message, db_session: AsyncSession, user: User):
    """Show service moderation options."""
    service_repo = ServiceRepository(db_session)
    services = await service_repo.get_all_services(limit=20)

    if not services:
        await message.answer("لم يتم العثور على خدمات.", reply_markup=get_admin_menu_keyboard())
        return

    services_text = "📤 إدارة الخدمات\n\n"
    for service in services[:10]:
        services_text += f"المعرف: {service.id} - {service.title}\n"
        services_text += f"مقدم الخدمة: {service.provider.full_name or 'غير متاح'}\n"
        services_text += f"الحالة: {humanize_enum(cast(ServiceStatus, service.status))}\n\n"

    services_text += "\nاستخدم /delete_service <id> لحذف خدمة."

    await message.answer(services_text, reply_markup=get_admin_menu_keyboard())


@router.message(F.text == "إدارة الطلبات")
@require_auth
@require_admin
async def show_request_moderation(message: Message, db_session: AsyncSession, user: User):
    """Show request moderation options."""
    request_repo = ServiceRequestRepository(db_session)
    requests = await request_repo.get_all_requests(limit=20)

    if not requests:
        await message.answer("لم يتم العثور على طلبات.", reply_markup=get_admin_menu_keyboard())
        return

    requests_text = "📥 إدارة الطلبات\n\n"
    for req in requests[:10]:
        requests_text += f"المعرف: {req.id} - {req.title}\n"
        requests_text += f"طالب الخدمة: {req.requester.full_name or 'غير متاح'}\n"
        requests_text += f"الحالة: {humanize_enum(cast(RequestStatus, req.status))}\n\n"

    requests_text += "\nاستخدم /delete_request <id> لحذف طلب."

    await message.answer(requests_text, reply_markup=get_admin_menu_keyboard())


@router.message(F.text == "إدارة المستخدمين")
@require_auth
@require_admin
async def show_user_management(message: Message, db_session: AsyncSession, user: User):
    """Show user management options."""
    user_repo = UserRepository(db_session)
    users = await user_repo.get_all_users(limit=20)

    if not users:
        await message.answer("لم يتم العثور على مستخدمين.", reply_markup=get_admin_menu_keyboard())
        return

    users_text = "👥 إدارة المستخدمين\n\n"
    for u in users[:10]:
        role_emoji = "👑" if u.role == UserRole.ADMIN else ("🎓" if u.is_student else "👤")
        users_text += f"{role_emoji} {u.full_name or 'غير متاح'} ({u.email})\n"
        users_text += (
            f"   الدور: {humanize_enum(u.role)}, طالب: {u.is_student}, نشط: {u.is_active}\n\n"
        )

    users_text += "\nاستخدم /promote_user <telegram_id> لترقية مستخدم إلى مدير."
    users_text += "\nاستخدم /disable_user <telegram_id> لتعطيل مستخدم."

    await message.answer(users_text, reply_markup=get_admin_menu_keyboard())


@router.message(F.text == "العودة للقائمة الرئيسية")
@require_auth
async def back_to_main_menu(message: Message, user: User):
    """Return to main menu."""
    await message.answer(
        "القائمة الرئيسية",
        reply_markup=get_main_menu_keyboard(bool(user.profile_completed), user.role.value, bool(user.is_student)),
    )


@router.callback_query(F.data.startswith("admin_approve:"))
@require_auth
@require_admin
async def admin_approve_item(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot):
    """Approve a service or request."""
    if not callback.data:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return

    item_type = parts[1]
    item_id = int(parts[2])

    if item_type == "service":
        service_repo = ServiceRepository(db_session)
        service = await service_repo.get_by_id(item_id)

        if not service:
            await callback.answer("الخدمة غير موجودة.", show_alert=True)
            return

        service_status = cast(ServiceStatus, service.status)
        if service_status != ServiceStatus.PENDING:
            await callback.answer("هذه الخدمة ليست في انتظار الموافقة.", show_alert=True)
            return

        from services.service_service import ServiceService

        service_service = ServiceService(db_session)

        try:
            service_text = f"🎯 {service.title}\n\n"
            service_text += f"📝 {service.description}\n\n"
            service_text += f"💰 السعر: {service_service.format_price(service)}\n"
            service_text += f"🎓 التخصص: {service.specialization}\n"
            service_text += f"✅ طالب معتمد"

            from handlers.keyboards import get_service_contact_keyboard

            # تصحيح type hint للـ id
            keyboard = get_service_contact_keyboard(int(service.id))  # type: ignore[arg-type]

            if service.media_file_id:
                # تصحيح type hint للـ media_file_id
                media_id = str(service.media_file_id)  # type: ignore[arg-type]

                if str(service.media_type) == "photo":
                    sent_message = await bot.send_photo(
                        config.SERVICES_CHANNEL_ID,
                        media_id,
                        caption=service_text,
                        reply_markup=keyboard,
                    )
                else:  # video
                    sent_message = await bot.send_video(
                        config.SERVICES_CHANNEL_ID,
                        media_id,
                        caption=service_text,
                        reply_markup=keyboard,
                    )
            else:
                sent_message = await bot.send_message(
                    config.SERVICES_CHANNEL_ID,
                    service_text,
                    reply_markup=keyboard,
                )

            # تعيين القيم بشكل صحيح
            service.channel_message_id = sent_message.message_id  # type: ignore[assignment]
            service.status = ServiceStatus.PUBLISHED  # type: ignore[assignment]
            await service_repo.update(service)

            provider = service.provider
            try:
                await bot.send_message(
                    provider.telegram_id,
                    f"✅ تم قبول وموافقة خدمتك '{service.title}' وتم نشرها في القناة!",
                )
            except Exception:
                pass

            # تحقق من نوع الرسالة قبل التعديل
            if isinstance(callback.message, TelegramMessage):
                try:
                    await bot.delete_message(config.ADMIN_GROUP_ID, callback.message.message_id)
                except Exception:
                    pass

            await callback.answer("✅ تم قبول الخدمة ونشرها!", show_alert=True)

            # تحقق من نوع الرسالة قبل edit_text
            if isinstance(callback.message, TelegramMessage):
                await callback.message.edit_text("✅ تم قبول الخدمة ونشرها في القناة.")

        except Exception as e:
            await callback.answer(f"خطأ في النشر: {e}", show_alert=True)

    elif item_type == "request":
        request_repo = ServiceRequestRepository(db_session)
        request = await request_repo.get_by_id(item_id)

        if not request:
            await callback.answer("الطلب غير موجود.", show_alert=True)
            return

        req_status = cast(RequestStatus, request.status)
        if req_status != RequestStatus.PENDING:
            await callback.answer("هذا الطلب ليس في انتظار الموافقة.", show_alert=True)
            return

        from services.request_service import RequestService

        request_service = RequestService(db_session)

        try:
            # allowed_specializations قد تكون Column[Any] في الموديل، نستخدم cast هنا
            allowed_specs = cast(Sequence[str] | None, request.allowed_specializations)
            if allowed_specs:
                specs_str = ", ".join(allowed_specs)
            else:
                specs_str = "غير محددة"

            request_text = "📋 طلب خدمة\n\n"
            request_text += f"📌 {request.title}\n\n"
            request_text += f"📝 {request.description}\n\n"
            request_text += f"🎓 التخصصات المطلوبة: {specs_str}\n"
            if request.preferred_gender:
                gender_names = {"male": "ذكر", "female": "أنثى"}
                gender_text = gender_names.get(str(request.preferred_gender), str(request.preferred_gender))
                request_text += f"⚧️ الجنس المفضل: {gender_text}\n"
            request_text += f"💰 الميزانية: {request_service.format_budget(request)}"

            from handlers.keyboards import get_request_offer_keyboard

            # تصحيح type hint للـ id
            keyboard = get_request_offer_keyboard(int(request.id))  # type: ignore[arg-type]

            sent_message = await bot.send_message(
                config.REQUESTS_CHANNEL_ID,
                request_text,
                reply_markup=keyboard,
            )

            request.channel_message_id = sent_message.message_id  # type: ignore[assignment]
            request.status = RequestStatus.PUBLISHED  # type: ignore[assignment]
            await request_repo.update(request)

            requester = request.requester
            try:
                await bot.send_message(
                    requester.telegram_id,
                    f"✅ تم قبول طلبك '{request.title}' وتم نشره في القناة!",
                )
            except Exception:
                pass

            # تحقق من نوع الرسالة قبل الحذف
            if isinstance(callback.message, TelegramMessage):
                try:
                    await bot.delete_message(config.ADMIN_GROUP_ID, callback.message.message_id)
                except Exception:
                    pass

            await callback.answer("✅ تم قبول الطلب ونشره!", show_alert=True)

            # تحقق من نوع الرسالة قبل edit_text
            if isinstance(callback.message, TelegramMessage):
                await callback.message.edit_text("✅ تم قبول الطلب ونشره في القناة.")

        except Exception as e:
            await callback.answer(f"خطأ في النشر: {e}", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject:"))
@require_auth
@require_admin
async def admin_reject_item(callback: CallbackQuery, db_session: AsyncSession, user: User, bot: Bot):
    """Reject a service or request."""
    if not callback.data:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("خطأ في البيانات.", show_alert=True)
        return

    item_type = parts[1]
    item_id = int(parts[2])

    if item_type == "service":
        service_repo = ServiceRepository(db_session)
        service = await service_repo.get_by_id(item_id)

        if not service:
            await callback.answer("الخدمة غير موجودة.", show_alert=True)
            return

        service_status = cast(ServiceStatus, service.status)
        if service_status != ServiceStatus.PENDING:
            await callback.answer("هذه الخدمة ليست في انتظار الموافقة.", show_alert=True)
            return

        service.status = ServiceStatus.REJECTED  # type: ignore[assignment]
        await service_repo.update(service)

        provider = service.provider
        try:
            await bot.send_message(
                provider.telegram_id,
                f"❌ تم رفض خدمتك '{service.title}' من قبل المشرفين.",
            )
        except Exception:
            pass

        # تحقق من نوع الرسالة قبل الحذف
        if isinstance(callback.message, TelegramMessage):
            try:
                await bot.delete_message(config.ADMIN_GROUP_ID, callback.message.message_id)
            except Exception:
                pass

        await callback.answer("❌ تم رفض الخدمة.", show_alert=True)

        # تحقق من نوع الرسالة قبل edit_text
        if isinstance(callback.message, TelegramMessage):
            await callback.message.edit_text("❌ تم رفض الخدمة.")

    elif item_type == "request":
        request_repo = ServiceRequestRepository(db_session)
        request = await request_repo.get_by_id(item_id)

        if not request:
            await callback.answer("الطلب غير موجود.", show_alert=True)
            return

        req_status = cast(RequestStatus, request.status)
        if req_status != RequestStatus.PENDING:
            await callback.answer("هذا الطلب ليس في انتظار الموافقة.", show_alert=True)
            return

        request.status = RequestStatus.REJECTED  # type: ignore[assignment]
        await request_repo.update(request)

        requester = request.requester
        try:
            await bot.send_message(
                requester.telegram_id,
                f"❌ تم رفض طلبك '{request.title}' من قبل المشرفين.",
            )
        except Exception:
            pass

        # تحقق من نوع الرسالة قبل الحذف
        if isinstance(callback.message, TelegramMessage):
            try:
                await bot.delete_message(config.ADMIN_GROUP_ID, callback.message.message_id)
            except Exception:
                pass

        await callback.answer("❌ تم رفض الطلب.", show_alert=True)

        # تحقق من نوع الرسالة قبل edit_text
        if isinstance(callback.message, TelegramMessage):
            await callback.message.edit_text("❌ تم رفض الطلب.")