"""Teacher handler for lecture and assignment management."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.keyboards import get_teacher_panel_keyboard
from handlers.common import require_auth, require_teacher
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Lecture
from repositories.teacher_repository import TeacherRepository
from typing import List

router = Router()


class LectureUploadStates(StatesGroup):
    """States for lecture upload flow."""
    waiting_for_subject_selection = State()
    waiting_for_lecture_files = State()
    waiting_for_lecture_title = State()


@router.message(F.text == "📤 رفع محاضرات")
@require_auth
@require_teacher
async def start_upload_lecture(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Start lecture upload process - show teacher's subjects."""
    teacher_repo = TeacherRepository(db_session)
    teacher_subjects = await teacher_repo.get_teacher_subjects(user.id, active_only=True)
    
    if not teacher_subjects:
        await message.answer(
            "❌ لا توجد مواد دراسية مرتبطة بحسابك.\n\n"
            "يرجى التواصل مع الإدارة لإضافة المواد الدراسية.",
            reply_markup=get_teacher_panel_keyboard()
        )
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
    
    await message.answer(
        "📚 <b>اختر المادة الدراسية:</b>\n\n"
        "اختر المادة التي تريد رفع محاضرة لها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(LectureUploadStates.waiting_for_subject_selection)


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
        
        await message.answer(
            f"✅ <b>تم رفع المحاضرة بنجاح!</b>\n\n"
            f"📚 المادة: <b>{subject_name}</b>\n"
            f"📁 عدد الملفات: <b>{len(uploaded_files)}</b> ملف\n\n"
            "يمكنك الآن رفع محاضرة أخرى أو العودة للقائمة الرئيسية.",
            parse_mode="HTML",
            reply_markup=get_teacher_panel_keyboard()
        )
        
        await state.clear()
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
    
    await callback.message.edit_text(
        f"✅ <b>تم رفع المحاضرة بنجاح!</b>\n\n"
        f"📚 المادة: <b>{subject_name}</b>\n"
        f"📁 عدد الملفات: <b>{len(uploaded_files)}</b> ملف\n\n"
        "يمكنك الآن رفع محاضرة أخرى أو العودة للقائمة الرئيسية.",
        parse_mode="HTML"
    )
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("✅ تم حفظ المحاضرة بنجاح!")
    
    await state.clear()


@router.callback_query(F.data == "lecture_cancel")
async def cancel_lecture_upload(callback: CallbackQuery, state: FSMContext):
    """Cancel lecture upload process."""
    await state.clear()
    await callback.message.edit_text("❌ تم إلغاء رفع المحاضرة.")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("تم الإلغاء")
