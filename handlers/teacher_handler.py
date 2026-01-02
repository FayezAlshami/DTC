"""Teacher handler for lecture and assignment management."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import get_teacher_panel_keyboard
from handlers.common import require_auth, require_teacher
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Lecture, Assignment, AssignmentSubmission, TeacherSubject, Subject
from repositories.teacher_repository import TeacherRepository
from typing import List

router = Router()


class LectureUploadStates(StatesGroup):
    """States for lecture upload flow."""
    waiting_for_subject_selection = State()
    waiting_for_lecture_files = State()
    waiting_for_lecture_title = State()


class AssignmentUploadStates(StatesGroup):
    """States for assignment upload flow."""
    waiting_for_subject_selection = State()
    waiting_for_assignment_files = State()
    waiting_for_assignment_title = State()


@router.message(F.text == "📤 رفع محاضرات")
@require_auth
@require_teacher
async def start_upload_lecture(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Start lecture management - show options."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await message.answer(
            "❌ لا توجد مواد دراسية مرتبطة بحسابك.\n\n"
            "يرجى التواصل مع الإدارة لإضافة المواد الدراسية.",
            reply_markup=get_teacher_panel_keyboard()
        )
        return
    
    # Build inline keyboard with options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ رفع محاضرة جديدة", callback_data="lecture_upload_new"))
    builder.add(InlineKeyboardButton(text="📋 إدارة المحاضرات", callback_data="lecture_manage"))
    builder.adjust(1)
    
    await message.answer(
        "📤 <b>إدارة المحاضرات</b>\n\n"
        "اختر الإجراء المطلوب:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "lecture_upload_new")
async def start_new_lecture_upload(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User):
    """Start new lecture upload - show teacher's subjects."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await callback.answer("❌ لا توجد مواد دراسية مرتبطة بحسابك.", show_alert=True)
        return
    
    # Build inline keyboard with subjects
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for teacher_subject in teacher_subjects:
        subject = teacher_subject.subject
        subject_name = subject.name
        if subject.code:
            subject_name = f"{subject_name} ({subject.code})"
        
        # Add academic year and semester if available
        if teacher_subject.academic_year or teacher_subject.semester:
            extra_info = []
            if teacher_subject.academic_year:
                extra_info.append(teacher_subject.academic_year)
            if teacher_subject.semester:
                extra_info.append(teacher_subject.semester)
            subject_name += f" - {'/'.join(extra_info)}"
        
        builder.add(InlineKeyboardButton(
            text=subject_name,
            callback_data=f"lecture_subject:{teacher_subject.id}"
        ))
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📚 <b>اختر المادة الدراسية:</b>\n\n"
        "اختر المادة التي تريد رفع محاضرة لها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(LectureUploadStates.waiting_for_subject_selection)
    await callback.answer()


@router.callback_query(F.data == "lecture_manage")
async def manage_lectures(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Show subjects to manage lectures."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await callback.answer("❌ لا توجد مواد دراسية مرتبطة بحسابك.", show_alert=True)
        return
    
    # Build inline keyboard with subjects
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for teacher_subject in teacher_subjects:
        subject = teacher_subject.subject
        subject_name = subject.name
        if subject.code:
            subject_name = f"{subject_name} ({subject.code})"
        
        # Add academic year and semester if available
        if teacher_subject.academic_year or teacher_subject.semester:
            extra_info = []
            if teacher_subject.academic_year:
                extra_info.append(teacher_subject.academic_year)
            if teacher_subject.semester:
                extra_info.append(teacher_subject.semester)
            subject_name += f" - {'/'.join(extra_info)}"
        
        builder.add(InlineKeyboardButton(
            text=subject_name,
            callback_data=f"lecture_manage_subject:{teacher_subject.id}"
        ))
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📋 <b>إدارة المحاضرات</b>\n\n"
        "اختر المادة التي تريد إدارة محاضراتها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lecture_manage_subject:"))
async def show_lectures_for_management(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Show lectures for a subject with management options."""
    teacher_subject_id = int(callback.data.split(":")[1])
    
    # Verify that this teacher_subject belongs to the teacher
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Get teacher_subject and subject info
    teacher_subject = None
    for ts in teacher_subjects:
        if ts.id == teacher_subject_id:
            teacher_subject = ts
            break
    
    if not teacher_subject:
        await callback.answer("❌ حدث خطأ في اختيار المادة.", show_alert=True)
        return
    
    # Get all lectures for this teacher_subject
    from sqlalchemy import select
    result = await db_session.execute(
        select(Lecture)
        .where(Lecture.teacher_subject_id == teacher_subject_id)
        .order_by(Lecture.display_order.asc())
    )
    lectures = result.scalars().all()
    
    if not lectures:
        await callback.message.edit_text(
            f"❌ <b>لا توجد محاضرات</b>\n\n"
            f"المادة: <b>{teacher_subject.subject.name}</b>\n\n"
            "لم يتم رفع أي محاضرات لهذه المادة بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Build message with lectures list
    subject_name = teacher_subject.subject.name
    if teacher_subject.subject.code:
        subject_name += f" ({teacher_subject.subject.code})"
    
    lectures_text = f"📋 <b>محاضرات المادة: {subject_name}</b>\n\n"
    lectures_text += f"📁 عدد المحاضرات: <b>{len(lectures)}</b>\n\n"
    lectures_text += "<b>قائمة المحاضرات:</b>\n"
    
    # Build inline keyboard with lecture management options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for idx, lecture in enumerate(lectures, 1):
        file_type_emoji = {
            "document": "📄",
            "photo": "🖼️",
            "video": "🎥",
            "audio": "🎵",
            "voice": "🎤",
            "video_note": "📹"
        }
        emoji = file_type_emoji.get(lecture.file_type, "📁")
        file_name = lecture.file_name or f"ملف {idx}"
        if len(file_name) > 30:
            file_name = file_name[:27] + "..."
        
        lectures_text += f"{idx}. {emoji} {file_name}\n"
        
        # Add management buttons for each lecture
        builder.add(InlineKeyboardButton(
            text=f"{idx} ⬆️",
            callback_data=f"lecture_move_up:{lecture.id}"
        ))
        builder.add(InlineKeyboardButton(
            text=f"{idx} ⬇️",
            callback_data=f"lecture_move_down:{lecture.id}"
        ))
        builder.add(InlineKeyboardButton(
            text=f"{idx} 🗑️",
            callback_data=f"lecture_delete:{lecture.id}"
        ))
    
    builder.adjust(3)  # 3 buttons per row
    
    # Add back button
    builder.row(InlineKeyboardButton(
        text="🔙 العودة",
        callback_data="lecture_manage"
    ))
    
    await callback.message.edit_text(
        lectures_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lecture_move_up:"))
async def move_lecture_up(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Move lecture up in order."""
    lecture_id = int(callback.data.split(":")[1])
    
    # Get lecture
    from sqlalchemy import select
    result = await db_session.execute(
        select(Lecture).where(Lecture.id == lecture_id)
    )
    lecture = result.scalar_one_or_none()
    
    if not lecture:
        await callback.answer("❌ المحاضرة غير موجودة.", show_alert=True)
        return
    
    # Verify ownership
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if lecture.teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه المحاضرة غير متاحة لك.", show_alert=True)
        return
    
    # Get previous lecture (with lower display_order)
    result = await db_session.execute(
        select(Lecture)
        .where(Lecture.teacher_subject_id == lecture.teacher_subject_id)
        .where(Lecture.display_order < lecture.display_order)
        .order_by(Lecture.display_order.desc())
        .limit(1)
    )
    prev_lecture = result.scalar_one_or_none()
    
    if not prev_lecture:
        await callback.answer("⚠️ هذه المحاضرة في المقدمة بالفعل.", show_alert=True)
        return
    
    # Swap display_order
    temp_order = lecture.display_order
    lecture.display_order = prev_lecture.display_order
    prev_lecture.display_order = temp_order
    
    await db_session.commit()
    await callback.answer("✅ تم نقل المحاضرة للأعلى")
    
    # Refresh the list
    await show_lectures_for_management(callback, db_session, user)


@router.callback_query(F.data.startswith("lecture_move_down:"))
async def move_lecture_down(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Move lecture down in order."""
    lecture_id = int(callback.data.split(":")[1])
    
    # Get lecture
    from sqlalchemy import select
    result = await db_session.execute(
        select(Lecture).where(Lecture.id == lecture_id)
    )
    lecture = result.scalar_one_or_none()
    
    if not lecture:
        await callback.answer("❌ المحاضرة غير موجودة.", show_alert=True)
        return
    
    # Verify ownership
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if lecture.teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه المحاضرة غير متاحة لك.", show_alert=True)
        return
    
    # Get next lecture (with higher display_order)
    result = await db_session.execute(
        select(Lecture)
        .where(Lecture.teacher_subject_id == lecture.teacher_subject_id)
        .where(Lecture.display_order > lecture.display_order)
        .order_by(Lecture.display_order.asc())
        .limit(1)
    )
    next_lecture = result.scalar_one_or_none()
    
    if not next_lecture:
        await callback.answer("⚠️ هذه المحاضرة في النهاية بالفعل.", show_alert=True)
        return
    
    # Swap display_order
    temp_order = lecture.display_order
    lecture.display_order = next_lecture.display_order
    next_lecture.display_order = temp_order
    
    await db_session.commit()
    await callback.answer("✅ تم نقل المحاضرة للأسفل")
    
    # Refresh the list
    await show_lectures_for_management(callback, db_session, user)


@router.callback_query(F.data.startswith("lecture_delete:"))
async def delete_lecture(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Delete a lecture."""
    lecture_id = int(callback.data.split(":")[1])
    
    # Get lecture
    from sqlalchemy import select
    result = await db_session.execute(
        select(Lecture).where(Lecture.id == lecture_id)
    )
    lecture = result.scalar_one_or_none()
    
    if not lecture:
        await callback.answer("❌ المحاضرة غير موجودة.", show_alert=True)
        return
    
    # Verify ownership
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if lecture.teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه المحاضرة غير متاحة لك.", show_alert=True)
        return
    
    # Store teacher_subject_id for refresh
    teacher_subject_id = lecture.teacher_subject_id
    
    # Delete lecture
    await db_session.delete(lecture)
    await db_session.commit()
    
    await callback.answer("✅ تم حذف المحاضرة")
    
    # Refresh the list
    callback.data = f"lecture_manage_subject:{teacher_subject_id}"
    await show_lectures_for_management(callback, db_session, user)


@router.callback_query(F.data.startswith("lecture_subject:"), LectureUploadStates.waiting_for_subject_selection)
async def process_subject_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User):
    """Process subject selection and ask for lecture files."""
    teacher_subject_id = int(callback.data.split(":")[1])
    
    # Verify that this teacher_subject belongs to the teacher
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Get subject info
    teacher_subject = None
    for ts in teacher_subjects:
        if ts.id == teacher_subject_id:
            teacher_subject = ts
            break
    
    if not teacher_subject:
        await callback.answer("❌ حدث خطأ في اختيار المادة.", show_alert=True)
        return
    
    subject_name = teacher_subject.subject.name
    
    await state.update_data(
        teacher_subject_id=teacher_subject_id,
        subject_name=subject_name,
        uploaded_files=[]  # List to store file info
    )
    
    await callback.message.edit_text(
        f"✅ تم اختيار المادة: <b>{subject_name}</b>\n\n"
        "📤 <b>الآن يمكنك رفع ملفات المحاضرة:</b>\n\n"
        "• يمكنك إرسال <b>أكثر من ملف</b> (مستندات، صور، فيديو، صوت)\n"
        "• الملفات سيتم حفظها بالترتيب الذي ترسله به\n"
        "• بعد الانتهاء من إرسال جميع الملفات، اكتب <b>'تم'</b> أو اضغط على زر 'إنهاء'",
        parse_mode="HTML"
    )
    
    # Add finish button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ إنهاء رفع الملفات", callback_data="lecture_finish_upload"))
    builder.add(InlineKeyboardButton(text="❌ إلغاء", callback_data="lecture_cancel"))
    builder.adjust(1)
    
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    
    await state.set_state(LectureUploadStates.waiting_for_lecture_files)
    await callback.answer()


@router.message(LectureUploadStates.waiting_for_lecture_files)
async def process_lecture_file(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Process uploaded lecture file."""
    data = await state.get_data()
    uploaded_files: List[dict] = data.get("uploaded_files", [])
    
    file_info = None
    file_type = None
    
    # Handle different file types
    if message.document:
        file_info = message.document
        file_type = "document"
    elif message.photo:
        # Get the largest photo
        file_info = message.photo[-1]
        file_type = "photo"
    elif message.video:
        file_info = message.video
        file_type = "video"
    elif message.audio:
        file_info = message.audio
        file_type = "audio"
    elif message.voice:
        file_info = message.voice
        file_type = "voice"
    elif message.video_note:
        file_info = message.video_note
        file_type = "video_note"
    elif message.text and message.text.lower() in ["تم", "finish", "done", "إنهاء"]:
        # User finished uploading files
        if not uploaded_files:
            await message.answer("❌ لم يتم رفع أي ملفات. يرجى إرسال ملف واحد على الأقل.")
            return
        
        # Save all files to database
        teacher_subject_id = data.get("teacher_subject_id")
        subject_name = data.get("subject_name", "المادة")
        
        # Get the maximum display_order for this teacher_subject
        from sqlalchemy import select, func
        result = await db_session.execute(
            select(func.max(Lecture.display_order)).where(
                Lecture.teacher_subject_id == teacher_subject_id
            )
        )
        max_order = result.scalar() or 0
        
        # Save all files
        for idx, file_data in enumerate(uploaded_files):
            lecture = Lecture(
                teacher_subject_id=teacher_subject_id,
                file_id=file_data["file_id"],
                file_type=file_data["file_type"],
                file_name=file_data.get("file_name"),
                file_size=file_data.get("file_size"),
                display_order=max_order + idx + 1
            )
            db_session.add(lecture)
        
        await db_session.commit()
        
        # Clear state FIRST before sending any messages
        await state.clear()
        
        await message.answer(
            f"✅ <b>تم رفع المحاضرة بنجاح!</b>\n\n"
            f"📚 المادة: <b>{subject_name}</b>\n"
            f"📁 عدد الملفات: <b>{len(uploaded_files)}</b> ملف\n\n"
            "يمكنك الآن رفع محاضرة أخرى أو العودة للقائمة الرئيسية.",
            parse_mode="HTML",
            reply_markup=get_teacher_panel_keyboard()
        )
        return
    
    if not file_info:
        await message.answer(
            "❌ يرجى إرسال ملف (مستند، صورة، فيديو، صوت) أو اكتب 'تم' لإنهاء رفع الملفات."
        )
        return
    
    # Extract file information
    file_id = file_info.file_id
    file_name = getattr(file_info, "file_name", None) or getattr(file_info, "file_unique_id", None)
    file_size = getattr(file_info, "file_size", None)
    
    # Add to uploaded files list
    uploaded_files.append({
        "file_id": file_id,
        "file_type": file_type,
        "file_name": file_name,
        "file_size": file_size
    })
    
    await state.update_data(uploaded_files=uploaded_files)
    
    # Confirm file received
    file_count = len(uploaded_files)
    await message.answer(
        f"✅ <b>تم استلام الملف {file_count}</b>\n\n"
        f"📁 نوع الملف: {file_type}\n"
        f"📊 إجمالي الملفات المرفوعة: {file_count}\n\n"
        "يمكنك إرسال ملف آخر أو اكتب 'تم' لإنهاء رفع الملفات.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "lecture_finish_upload", LectureUploadStates.waiting_for_lecture_files)
async def finish_lecture_upload(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User):
    """Finish lecture upload process."""
    data = await state.get_data()
    uploaded_files: List[dict] = data.get("uploaded_files", [])
    
    if not uploaded_files:
        await callback.answer("❌ لم يتم رفع أي ملفات. يرجى إرسال ملف واحد على الأقل.", show_alert=True)
        return
    
    # Save all files to database
    teacher_subject_id = data.get("teacher_subject_id")
    subject_name = data.get("subject_name", "المادة")
    
    # Get the maximum display_order for this teacher_subject
    from sqlalchemy import select, func
    result = await db_session.execute(
        select(func.max(Lecture.display_order)).where(
            Lecture.teacher_subject_id == teacher_subject_id
        )
    )
    max_order = result.scalar() or 0
    
    # Save all files
    for idx, file_data in enumerate(uploaded_files):
        lecture = Lecture(
            teacher_subject_id=teacher_subject_id,
            file_id=file_data["file_id"],
            file_type=file_data["file_type"],
            file_name=file_data.get("file_name"),
            file_size=file_data.get("file_size"),
            display_order=max_order + idx + 1
        )
        db_session.add(lecture)
    
    await db_session.commit()
    
    # Clear state FIRST before sending any messages
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ <b>تم رفع المحاضرة بنجاح!</b>\n\n"
        f"📚 المادة: <b>{subject_name}</b>\n"
        f"📁 عدد الملفات: <b>{len(uploaded_files)}</b> ملف\n\n"
        "يمكنك الآن رفع محاضرة أخرى أو العودة للقائمة الرئيسية.",
        parse_mode="HTML"
    )
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("✅ تم حفظ المحاضرة بنجاح!")


@router.callback_query(F.data == "lecture_cancel")
async def cancel_lecture_upload(callback: CallbackQuery, state: FSMContext):
    """Cancel lecture upload process."""
    await state.clear()
    await callback.message.edit_text("❌ تم إلغاء رفع المحاضرة.")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("تم الإلغاء")


# ==================== ASSIGNMENT UPLOAD HANDLERS ====================

@router.message(F.text == "📝 رفع وظائف")
@require_auth
@require_teacher
async def start_upload_assignment(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Start assignment management - show options."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await message.answer(
            "❌ لا توجد مواد دراسية مرتبطة بحسابك.\n\n"
            "يرجى التواصل مع الإدارة لإضافة المواد الدراسية.",
            reply_markup=get_teacher_panel_keyboard()
        )
        return
    
    # Build inline keyboard with options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ رفع وظيفة جديدة", callback_data="assignment_upload_new"))
    builder.add(InlineKeyboardButton(text="📋 إدارة الوظائف", callback_data="assignment_manage"))
    builder.adjust(1)
    
    await message.answer(
        "📝 <b>إدارة الوظائف</b>\n\n"
        "اختر الإجراء المطلوب:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "assignment_upload_new")
async def start_new_assignment_upload(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User):
    """Start new assignment upload - show teacher's subjects."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await callback.answer("❌ لا توجد مواد دراسية مرتبطة بحسابك.", show_alert=True)
        return
    
    # Build inline keyboard with subjects
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for teacher_subject in teacher_subjects:
        subject = teacher_subject.subject
        subject_name = subject.name
        if subject.code:
            subject_name = f"{subject_name} ({subject.code})"
        
        # Add academic year and semester if available
        if teacher_subject.academic_year or teacher_subject.semester:
            extra_info = []
            if teacher_subject.academic_year:
                extra_info.append(teacher_subject.academic_year)
            if teacher_subject.semester:
                extra_info.append(teacher_subject.semester)
            subject_name += f" - {'/'.join(extra_info)}"
        
        builder.add(InlineKeyboardButton(
            text=subject_name,
            callback_data=f"assignment_subject:{teacher_subject.id}"
        ))
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📚 <b>اختر المادة الدراسية:</b>\n\n"
        "اختر المادة التي تريد رفع وظيفة لها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(AssignmentUploadStates.waiting_for_subject_selection)
    await callback.answer()


@router.callback_query(F.data == "assignment_manage")
async def manage_assignments(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Show subjects to manage assignments."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await callback.answer("❌ لا توجد مواد دراسية مرتبطة بحسابك.", show_alert=True)
        return
    
    # Build inline keyboard with subjects
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for teacher_subject in teacher_subjects:
        subject = teacher_subject.subject
        subject_name = subject.name
        if subject.code:
            subject_name = f"{subject_name} ({subject.code})"
        
        # Add academic year and semester if available
        if teacher_subject.academic_year or teacher_subject.semester:
            extra_info = []
            if teacher_subject.academic_year:
                extra_info.append(teacher_subject.academic_year)
            if teacher_subject.semester:
                extra_info.append(teacher_subject.semester)
            subject_name += f" - {'/'.join(extra_info)}"
        
        builder.add(InlineKeyboardButton(
            text=subject_name,
            callback_data=f"assignment_manage_subject:{teacher_subject.id}"
        ))
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📋 <b>إدارة الوظائف</b>\n\n"
        "اختر المادة التي تريد إدارة وظائفها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("assignment_manage_subject:"))
async def show_assignments_for_management(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Show assignments for a subject with management options."""
    teacher_subject_id = int(callback.data.split(":")[1])
    
    # Verify that this teacher_subject belongs to the teacher
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Get teacher_subject and subject info
    teacher_subject = None
    for ts in teacher_subjects:
        if ts.id == teacher_subject_id:
            teacher_subject = ts
            break
    
    if not teacher_subject:
        await callback.answer("❌ حدث خطأ في اختيار المادة.", show_alert=True)
        return
    
    # Get all assignments for this teacher_subject
    from sqlalchemy import select
    result = await db_session.execute(
        select(Assignment)
        .where(Assignment.teacher_subject_id == teacher_subject_id)
        .order_by(Assignment.display_order.asc())
    )
    assignments = result.scalars().all()
    
    if not assignments:
        await callback.message.edit_text(
            f"❌ <b>لا توجد وظائف</b>\n\n"
            f"المادة: <b>{teacher_subject.subject.name}</b>\n\n"
            "لم يتم رفع أي وظائف لهذه المادة بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Build message with assignments list
    subject_name = teacher_subject.subject.name
    if teacher_subject.subject.code:
        subject_name += f" ({teacher_subject.subject.code})"
    
    assignments_text = f"📋 <b>وظائف المادة: {subject_name}</b>\n\n"
    assignments_text += f"📁 عدد الوظائف: <b>{len(assignments)}</b>\n\n"
    assignments_text += "<b>قائمة الوظائف:</b>\n"
    
    # Build inline keyboard with assignment management options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for idx, assignment in enumerate(assignments, 1):
        file_type_emoji = {
            "document": "📄",
            "photo": "🖼️",
            "video": "🎥",
            "audio": "🎵",
            "voice": "🎤",
            "video_note": "📹"
        }
        emoji = file_type_emoji.get(assignment.file_type, "📁")
        file_name = assignment.file_name or f"ملف {idx}"
        if len(file_name) > 30:
            file_name = file_name[:27] + "..."
        
        assignments_text += f"{idx}. {emoji} {file_name}\n"
        
        # Add management buttons for each assignment
        builder.add(InlineKeyboardButton(
            text=f"{idx} ⬆️",
            callback_data=f"assignment_move_up:{assignment.id}"
        ))
        builder.add(InlineKeyboardButton(
            text=f"{idx} ⬇️",
            callback_data=f"assignment_move_down:{assignment.id}"
        ))
        builder.add(InlineKeyboardButton(
            text=f"{idx} 🗑️",
            callback_data=f"assignment_delete:{assignment.id}"
        ))
    
    builder.adjust(3)  # 3 buttons per row
    
    # Add back button
    builder.row(InlineKeyboardButton(
        text="🔙 العودة",
        callback_data="assignment_manage"
    ))
    
    await callback.message.edit_text(
        assignments_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("assignment_subject:"), AssignmentUploadStates.waiting_for_subject_selection)
async def process_assignment_subject_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User):
    """Process subject selection and ask for assignment files."""
    teacher_subject_id = int(callback.data.split(":")[1])
    
    # Verify that this teacher_subject belongs to the teacher
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Get subject info
    teacher_subject = None
    for ts in teacher_subjects:
        if ts.id == teacher_subject_id:
            teacher_subject = ts
            break
    
    if not teacher_subject:
        await callback.answer("❌ حدث خطأ في اختيار المادة.", show_alert=True)
        return
    
    subject_name = teacher_subject.subject.name
    
    await state.update_data(
        teacher_subject_id=teacher_subject_id,
        subject_name=subject_name,
        uploaded_files=[]  # List to store file info
    )
    
    await callback.message.edit_text(
        f"✅ تم اختيار المادة: <b>{subject_name}</b>\n\n"
        "📤 <b>الآن يمكنك رفع ملفات الوظيفة:</b>\n\n"
        "• يمكنك إرسال <b>أكثر من ملف</b> (مستندات، صور، فيديو، صوت)\n"
        "• الملفات سيتم حفظها بالترتيب الذي ترسله به\n"
        "• بعد الانتهاء من إرسال جميع الملفات، اكتب <b>'تم'</b> أو اضغط على زر 'إنهاء'",
        parse_mode="HTML"
    )
    
    # Add finish button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ إنهاء رفع الملفات", callback_data="assignment_finish_upload"))
    builder.add(InlineKeyboardButton(text="❌ إلغاء", callback_data="assignment_cancel"))
    builder.adjust(1)
    
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    
    await state.set_state(AssignmentUploadStates.waiting_for_assignment_files)
    await callback.answer()


@router.message(AssignmentUploadStates.waiting_for_assignment_files)
async def process_assignment_file(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Process uploaded assignment file."""
    data = await state.get_data()
    uploaded_files: List[dict] = data.get("uploaded_files", [])
    
    file_info = None
    file_type = None
    
    # Handle different file types
    if message.document:
        file_info = message.document
        file_type = "document"
    elif message.photo:
        # Get the largest photo
        file_info = message.photo[-1]
        file_type = "photo"
    elif message.video:
        file_info = message.video
        file_type = "video"
    elif message.audio:
        file_info = message.audio
        file_type = "audio"
    elif message.voice:
        file_info = message.voice
        file_type = "voice"
    elif message.video_note:
        file_info = message.video_note
        file_type = "video_note"
    elif message.text and message.text.lower() in ["تم", "finish", "done", "إنهاء"]:
        # User finished uploading files
        if not uploaded_files:
            await message.answer("❌ لم يتم رفع أي ملفات. يرجى إرسال ملف واحد على الأقل.")
            return
        
        # Save all files to database
        teacher_subject_id = data.get("teacher_subject_id")
        subject_name = data.get("subject_name", "المادة")
        
        # Get the maximum display_order for this teacher_subject
        from sqlalchemy import select, func
        result = await db_session.execute(
            select(func.max(Assignment.display_order)).where(
                Assignment.teacher_subject_id == teacher_subject_id
            )
        )
        max_order = result.scalar() or 0
        
        # Save all files
        for idx, file_data in enumerate(uploaded_files):
            assignment = Assignment(
                teacher_subject_id=teacher_subject_id,
                file_id=file_data["file_id"],
                file_type=file_data["file_type"],
                file_name=file_data.get("file_name"),
                file_size=file_data.get("file_size"),
                display_order=max_order + idx + 1
            )
            db_session.add(assignment)
        
        await db_session.commit()
        
        # Clear state FIRST before sending any messages
        await state.clear()
        
        await message.answer(
            f"✅ <b>تم رفع الوظيفة بنجاح!</b>\n\n"
            f"📚 المادة: <b>{subject_name}</b>\n"
            f"📁 عدد الملفات: <b>{len(uploaded_files)}</b> ملف\n\n"
            "يمكنك الآن رفع وظيفة أخرى أو العودة للقائمة الرئيسية.",
            parse_mode="HTML",
            reply_markup=get_teacher_panel_keyboard()
        )
        return
    
    if not file_info:
        await message.answer(
            "❌ يرجى إرسال ملف (مستند، صورة، فيديو، صوت) أو اكتب 'تم' لإنهاء رفع الملفات."
        )
        return
    
    # Extract file information
    file_id = file_info.file_id
    file_name = getattr(file_info, "file_name", None) or getattr(file_info, "file_unique_id", None)
    file_size = getattr(file_info, "file_size", None)
    
    # Add to uploaded files list
    uploaded_files.append({
        "file_id": file_id,
        "file_type": file_type,
        "file_name": file_name,
        "file_size": file_size
    })
    
    await state.update_data(uploaded_files=uploaded_files)
    
    # Confirm file received
    file_count = len(uploaded_files)
    await message.answer(
        f"✅ <b>تم استلام الملف {file_count}</b>\n\n"
        f"📁 نوع الملف: {file_type}\n"
        f"📊 إجمالي الملفات المرفوعة: {file_count}\n\n"
        "يمكنك إرسال ملف آخر أو اكتب 'تم' لإنهاء رفع الملفات.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "assignment_finish_upload", AssignmentUploadStates.waiting_for_assignment_files)
async def finish_assignment_upload(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User):
    """Finish assignment upload process."""
    data = await state.get_data()
    uploaded_files: List[dict] = data.get("uploaded_files", [])
    
    if not uploaded_files:
        await callback.answer("❌ لم يتم رفع أي ملفات. يرجى إرسال ملف واحد على الأقل.", show_alert=True)
        return
    
    # Save all files to database
    teacher_subject_id = data.get("teacher_subject_id")
    subject_name = data.get("subject_name", "المادة")
    
    # Get the maximum display_order for this teacher_subject
    from sqlalchemy import select, func
    result = await db_session.execute(
        select(func.max(Assignment.display_order)).where(
            Assignment.teacher_subject_id == teacher_subject_id
        )
    )
    max_order = result.scalar() or 0
    
    # Save all files
    for idx, file_data in enumerate(uploaded_files):
        assignment = Assignment(
            teacher_subject_id=teacher_subject_id,
            file_id=file_data["file_id"],
            file_type=file_data["file_type"],
            file_name=file_data.get("file_name"),
            file_size=file_data.get("file_size"),
            display_order=max_order + idx + 1
        )
        db_session.add(assignment)
    
    await db_session.commit()
    
    # Clear state FIRST before sending any messages
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ <b>تم رفع الوظيفة بنجاح!</b>\n\n"
        f"📚 المادة: <b>{subject_name}</b>\n"
        f"📁 عدد الملفات: <b>{len(uploaded_files)}</b> ملف\n\n"
        "يمكنك الآن رفع وظيفة أخرى أو العودة للقائمة الرئيسية.",
        parse_mode="HTML"
    )
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("✅ تم حفظ الوظيفة بنجاح!")


@router.callback_query(F.data == "assignment_cancel")
async def cancel_assignment_upload(callback: CallbackQuery, state: FSMContext):
    """Cancel assignment upload process."""
    await state.clear()
    await callback.message.edit_text("❌ تم إلغاء رفع الوظيفة.")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("تم الإلغاء")


@router.callback_query(F.data.startswith("assignment_move_up:"))
async def move_assignment_up(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Move assignment up in order."""
    assignment_id = int(callback.data.split(":")[1])
    
    # Get assignment
    from sqlalchemy import select
    result = await db_session.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        await callback.answer("❌ الوظيفة غير موجودة.", show_alert=True)
        return
    
    # Verify ownership
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if assignment.teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه الوظيفة غير متاحة لك.", show_alert=True)
        return
    
    # Get previous assignment (with lower display_order)
    result = await db_session.execute(
        select(Assignment)
        .where(Assignment.teacher_subject_id == assignment.teacher_subject_id)
        .where(Assignment.display_order < assignment.display_order)
        .order_by(Assignment.display_order.desc())
        .limit(1)
    )
    prev_assignment = result.scalar_one_or_none()
    
    if not prev_assignment:
        await callback.answer("⚠️ هذه الوظيفة في المقدمة بالفعل.", show_alert=True)
        return
    
    # Swap display_order
    temp_order = assignment.display_order
    assignment.display_order = prev_assignment.display_order
    prev_assignment.display_order = temp_order
    
    await db_session.commit()
    await callback.answer("✅ تم نقل الوظيفة للأعلى")
    
    # Refresh the list
    await show_assignments_for_management(callback, db_session, user)


@router.callback_query(F.data.startswith("assignment_move_down:"))
async def move_assignment_down(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Move assignment down in order."""
    assignment_id = int(callback.data.split(":")[1])
    
    # Get assignment
    from sqlalchemy import select
    result = await db_session.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        await callback.answer("❌ الوظيفة غير موجودة.", show_alert=True)
        return
    
    # Verify ownership
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if assignment.teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه الوظيفة غير متاحة لك.", show_alert=True)
        return
    
    # Get next assignment (with higher display_order)
    result = await db_session.execute(
        select(Assignment)
        .where(Assignment.teacher_subject_id == assignment.teacher_subject_id)
        .where(Assignment.display_order > assignment.display_order)
        .order_by(Assignment.display_order.asc())
        .limit(1)
    )
    next_assignment = result.scalar_one_or_none()
    
    if not next_assignment:
        await callback.answer("⚠️ هذه الوظيفة في النهاية بالفعل.", show_alert=True)
        return
    
    # Swap display_order
    temp_order = assignment.display_order
    assignment.display_order = next_assignment.display_order
    next_assignment.display_order = temp_order
    
    await db_session.commit()
    await callback.answer("✅ تم نقل الوظيفة للأسفل")
    
    # Refresh the list
    await show_assignments_for_management(callback, db_session, user)


@router.callback_query(F.data.startswith("assignment_delete:"))
async def delete_assignment(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Delete an assignment."""
    assignment_id = int(callback.data.split(":")[1])
    
    # Get assignment
    from sqlalchemy import select
    result = await db_session.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        await callback.answer("❌ الوظيفة غير موجودة.", show_alert=True)
        return
    
    # Verify ownership
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    if assignment.teacher_subject_id not in teacher_subject_ids:
        await callback.answer("❌ هذه الوظيفة غير متاحة لك.", show_alert=True)
        return
    
    # Store teacher_subject_id for refresh
    teacher_subject_id = assignment.teacher_subject_id
    
    # Delete assignment
    await db_session.delete(assignment)
    await db_session.commit()
    
    await callback.answer("✅ تم حذف الوظيفة")
    
    # Refresh the list
    callback.data = f"assignment_manage_subject:{teacher_subject_id}"
    await show_assignments_for_management(callback, db_session, user)


@router.message(F.text == "📥 تنزيل وظائف الطلاب")
@require_auth
@require_teacher
async def start_download_student_assignments(message: Message, db_session: AsyncSession, user: User):
    """Start download student assignments - show teacher's subjects."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await message.answer(
            "❌ لا توجد مواد دراسية مرتبطة بحسابك.\n\n"
            "يرجى التواصل مع الإدارة لإضافة المواد الدراسية.",
            reply_markup=get_teacher_panel_keyboard()
        )
        return
    
    # Get unique subjects
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    subject_ids = [ts.subject_id for ts in teacher_subjects]
    result = await db_session.execute(
        select(Subject)
        .where(Subject.id.in_(subject_ids))
        .where(Subject.is_active == True)
    )
    subjects = result.scalars().all()
    
    if not subjects:
        await message.answer(
            "❌ لا توجد مواد دراسية نشطة مرتبطة بحسابك.",
            reply_markup=get_teacher_panel_keyboard()
        )
        return
    
    # Build inline keyboard with subjects
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for subject in subjects:
        subject_name = subject.name
        if subject.code:
            subject_name = f"{subject_name} ({subject.code})"
        
        builder.add(InlineKeyboardButton(
            text=subject_name,
            callback_data=f"teacher_download_submissions:{subject.id}"
        ))
    
    builder.adjust(1)
    
    await message.answer(
        "📥 <b>تنزيل وظائف الطلاب</b>\n\n"
        "اختر المادة التي تريد عرض وظائف الطلاب الخاصة بها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("teacher_download_submissions:"))
async def download_student_assignments(callback: CallbackQuery, bot, db_session: AsyncSession, user: User):
    """Download all student assignment submissions for selected subject."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    subject_id = int(callback.data.split(":")[1])
    
    # Verify teacher teaches this subject
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    teacher_subject_ids = [ts.id for ts in teacher_subjects]
    
    # Get subject
    result = await db_session.execute(
        select(Subject).where(Subject.id == subject_id)
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        await callback.answer("❌ المادة غير موجودة.", show_alert=True)
        return
    
    # Verify teacher teaches this subject
    teacher_subject = None
    for ts in teacher_subjects:
        if ts.subject_id == subject_id:
            teacher_subject = ts
            break
    
    if not teacher_subject:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Get all assignments for this teacher_subject
    assignments_result = await db_session.execute(
        select(Assignment)
        .where(Assignment.teacher_subject_id == teacher_subject.id)
    )
    assignments = assignments_result.scalars().all()
    
    if not assignments:
        await callback.message.edit_text(
            f"❌ <b>لا توجد وظائف</b>\n\n"
            f"المادة: <b>{subject.name}</b>\n\n"
            "لم يتم رفع أي وظائف لهذه المادة بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Get all submissions for these assignments
    assignment_ids = [a.id for a in assignments]
    submissions_result = await db_session.execute(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.assignment_id.in_(assignment_ids))
        .options(selectinload(AssignmentSubmission.student))
        .order_by(AssignmentSubmission.created_at.desc())
    )
    submissions = submissions_result.scalars().all()
    
    if not submissions:
        await callback.message.edit_text(
            f"❌ <b>لا توجد حلول للوظائف</b>\n\n"
            f"المادة: <b>{subject.name}</b>\n\n"
            "لم يرفع أي طالب حلول للوظائف بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Send subject info
    subject_info = f"📚 <b>{subject.name}</b>"
    if subject.code:
        subject_info += f" ({subject.code})"
    subject_info += f"\n\n📁 عدد الحلول: <b>{len(submissions)}</b> ملف\n\n"
    
    await callback.message.edit_text(
        subject_info + "⏳ جاري إرسال ملفات الوظائف...",
        parse_mode="HTML"
    )
    await callback.answer()
    
    # Send all submission files with student info
    sent_count = 0
    for idx, submission in enumerate(submissions, 1):
        try:
            # Get student info
            student = submission.student
            student_name = student.full_name or "غير محدد"
            student_id = student.student_id or "غير محدد"
            
            # Build caption with student info
            caption = (
                f"📝 <b>حل الوظيفة {idx}/{len(submissions)}</b>\n\n"
                f"👤 <b>الطالب:</b> {student_name}\n"
                f"🆔 <b>الرقم:</b> {student_id}\n"
            )
            if submission.file_name:
                caption += f"\n📄 <b>الملف:</b> {submission.file_name}"
            
            # Send file based on type
            if submission.file_type == "document":
                await bot.send_document(
                    chat_id=user.telegram_id,
                    document=submission.file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            elif submission.file_type == "photo":
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=submission.file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                # Fallback: send as document
                await bot.send_document(
                    chat_id=user.telegram_id,
                    document=submission.file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            
            sent_count += 1
            
            # Small delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(0.5)
            
        except Exception as e:
            # Log error but continue sending other files
            print(f"Error sending submission {submission.id}: {e}")
            continue
    
    # Send completion message
    if sent_count > 0:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=f"✅ <b>تم إرسال {sent_count} من {len(submissions)} حل</b>\n\n"
                 f"المادة: <b>{subject.name}</b>\n\n"
                 "يمكنك اختيار مادة أخرى أو العودة للقائمة.",
            parse_mode="HTML",
            reply_markup=get_teacher_panel_keyboard()
        )
    else:
        await bot.send_message(
            chat_id=user.telegram_id,
            text="❌ حدث خطأ أثناء إرسال ملفات الوظائف.\n\n"
                 "يرجى المحاولة مرة أخرى لاحقاً.",
            reply_markup=get_teacher_panel_keyboard()
        )
