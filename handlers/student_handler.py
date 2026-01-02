"""Student handler for e-learning features."""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from handlers.keyboards import get_e_learning_keyboard, get_main_menu_keyboard
from handlers.common import require_auth, require_student
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database.models import User, Subject, TeacherSubject, Lecture, Assignment, AssignmentSubmission, Specialization
from repositories.subject_repository import SubjectRepository
from repositories.teacher_repository import TeacherRepository
from typing import List

router = Router()

# FSM States for assignment upload
from aiogram.fsm.state import State, StatesGroup

class AssignmentUploadStates(StatesGroup):
    waiting_for_assignment_file = State()


@router.message(F.text == "🎓 التعلّم الإلكتروني")
@require_auth
@require_student
async def show_e_learning_menu(message: Message, user: User):
    """Show e-learning menu for students."""
    await message.answer(
        "🎓 <b>التعلّم الإلكتروني</b>\n\n"
        "اختر الخيار المطلوب:",
        parse_mode="HTML",
        reply_markup=get_e_learning_keyboard()
    )


@router.message(F.text == "📚 محاضرات")
@require_auth
@require_student
async def show_lectures_menu(message: Message, state: FSMContext, db_session: AsyncSession, user: User, bot: Bot):
    """Show student's specialization subjects for lecture selection."""
    # Check if student has specialization
    if not user.specialization_id:
        await message.answer(
            "❌ لم يتم تحديد التخصص الخاص بك.\n\n"
            "يرجى إكمال ملفك الشخصي أولاً.",
            reply_markup=get_e_learning_keyboard()
        )
        return
    
    # Get student's specialization
    from repositories.specialization_repository import SpecializationRepository
    spec_repo = SpecializationRepository(db_session)
    specialization = await spec_repo.get_by_id(user.specialization_id)
    
    if not specialization:
        await message.answer(
            "❌ التخصص الخاص بك غير موجود في النظام.",
            reply_markup=get_e_learning_keyboard()
        )
        return
    
    # Get all active subjects for this specialization
    subject_repo = SubjectRepository(db_session)
    subjects = await subject_repo.get_by_specialization(user.specialization_id, active_only=True)
    
    if not subjects:
        await message.answer(
            f"❌ لا توجد مواد دراسية متاحة لتخصص <b>{specialization.name}</b>.",
            parse_mode="HTML",
            reply_markup=get_e_learning_keyboard()
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
            callback_data=f"student_lecture_subject:{subject.id}"
        ))
    
    builder.adjust(1)
    
    await message.answer(
        f"📚 <b>اختر المادة الدراسية:</b>\n\n"
        f"التخصص: <b>{specialization.name}</b>\n\n"
        "اختر المادة التي تريد عرض محاضراتها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("student_lecture_subject:"))
async def show_lectures_for_subject(callback: CallbackQuery, bot: Bot, db_session: AsyncSession, user: User):
    """Show lectures for selected subject."""
    subject_id = int(callback.data.split(":")[1])
    
    # Verify subject belongs to student's specialization
    if not user.specialization_id:
        await callback.answer("❌ لم يتم تحديد التخصص الخاص بك.", show_alert=True)
        return
    
    subject_repo = SubjectRepository(db_session)
    subject = await subject_repo.get_by_id(subject_id)
    
    if not subject or subject.specialization_id != user.specialization_id:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Get all teacher_subjects for this subject
    result = await db_session.execute(
        select(TeacherSubject)
        .where(TeacherSubject.subject_id == subject_id)
        .where(TeacherSubject.is_active == True)
        .options(selectinload(TeacherSubject.lectures))
    )
    teacher_subjects = result.scalars().all()
    
    # Collect all lectures from all teachers for this subject
    all_lectures: List[Lecture] = []
    for teacher_subject in teacher_subjects:
        # Get lectures ordered by display_order
        lectures_result = await db_session.execute(
            select(Lecture)
            .where(Lecture.teacher_subject_id == teacher_subject.id)
            .order_by(Lecture.display_order.asc())
        )
        lectures = lectures_result.scalars().all()
        all_lectures.extend(lectures)
    
    if not all_lectures:
        await callback.message.edit_text(
            f"❌ <b>لا توجد محاضرات متاحة</b>\n\n"
            f"المادة: <b>{subject.name}</b>\n\n"
            "لم يتم رفع أي محاضرات لهذه المادة بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Send subject info
    subject_info = f"📚 <b>{subject.name}</b>"
    if subject.code:
        subject_info += f" ({subject.code})"
    subject_info += f"\n\n📁 عدد المحاضرات: <b>{len(all_lectures)}</b> ملف\n\n"
    
    await callback.message.edit_text(
        subject_info + "⏳ جاري إرسال المحاضرات...",
        parse_mode="HTML"
    )
    await callback.answer()
    
    # Send all lecture files
    sent_count = 0
    for idx, lecture in enumerate(all_lectures, 1):
        try:
            # Send file based on type
            if lecture.file_type == "document":
                await bot.send_document(
                    chat_id=user.telegram_id,
                    document=lecture.file_id,
                    caption=f"📄 المحاضرة {idx}/{len(all_lectures)}" + (f" - {lecture.file_name}" if lecture.file_name else "")
                )
            elif lecture.file_type == "photo":
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=lecture.file_id,
                    caption=f"🖼️ المحاضرة {idx}/{len(all_lectures)}"
                )
            elif lecture.file_type == "video":
                await bot.send_video(
                    chat_id=user.telegram_id,
                    video=lecture.file_id,
                    caption=f"🎥 المحاضرة {idx}/{len(all_lectures)}"
                )
            elif lecture.file_type == "audio":
                await bot.send_audio(
                    chat_id=user.telegram_id,
                    audio=lecture.file_id,
                    caption=f"🎵 المحاضرة {idx}/{len(all_lectures)}"
                )
            elif lecture.file_type == "voice":
                await bot.send_voice(
                    chat_id=user.telegram_id,
                    voice=lecture.file_id,
                    caption=f"🎤 المحاضرة {idx}/{len(all_lectures)}"
                )
            elif lecture.file_type == "video_note":
                await bot.send_video_note(
                    chat_id=user.telegram_id,
                    video_note=lecture.file_id
                )
            else:
                # Fallback: send as document
                await bot.send_document(
                    chat_id=user.telegram_id,
                    document=lecture.file_id,
                    caption=f"📄 المحاضرة {idx}/{len(all_lectures)}"
                )
            
            sent_count += 1
            
            # Small delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(0.5)
            
        except Exception as e:
            # Log error but continue sending other files
            print(f"Error sending lecture {lecture.id}: {e}")
            continue
    
    # Send completion message
    if sent_count > 0:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=f"✅ <b>تم إرسال {sent_count} من {len(all_lectures)} محاضرة</b>\n\n"
                 "يمكنك اختيار مادة أخرى أو العودة للقائمة.",
            parse_mode="HTML",
            reply_markup=get_e_learning_keyboard()
        )
    else:
        await bot.send_message(
            chat_id=user.telegram_id,
            text="❌ حدث خطأ أثناء إرسال المحاضرات.\n\n"
                 "يرجى المحاولة مرة أخرى لاحقاً.",
            reply_markup=get_e_learning_keyboard()
        )


@router.message(F.text == "📝 وظائف")
@require_auth
@require_student
async def show_assignments_menu(message: Message, db_session: AsyncSession, user: User):
    """Show assignments menu with download and upload options."""
    # Build inline keyboard with options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📥 تحميل", callback_data="assignment_download"))
    builder.add(InlineKeyboardButton(text="📤 رفع", callback_data="assignment_upload_student"))
    builder.adjust(2)
    
    await message.answer(
        "📝 <b>الوظائف</b>\n\n"
        "اختر الإجراء المطلوب:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "assignment_download")
async def show_assignments_subjects(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Show subjects that have assignments for download."""
    # Check if student has specialization
    if not user.specialization_id:
        await callback.answer("❌ لم يتم تحديد التخصص الخاص بك.", show_alert=True)
        return
    
    # Get student's specialization
    from repositories.specialization_repository import SpecializationRepository
    spec_repo = SpecializationRepository(db_session)
    specialization = await spec_repo.get_by_id(user.specialization_id)
    
    if not specialization:
        await callback.answer("❌ التخصص الخاص بك غير موجود في النظام.", show_alert=True)
        return
    
    # Get all active subjects for this specialization
    subject_repo = SubjectRepository(db_session)
    subjects = await subject_repo.get_by_specialization(user.specialization_id, active_only=True)
    
    if not subjects:
        await callback.message.edit_text(
            f"❌ لا توجد مواد دراسية متاحة لتخصص <b>{specialization.name}</b>.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Get all teacher_subjects for these subjects and check which ones have assignments
    subjects_with_assignments = []
    for subject in subjects:
        # Get all teacher_subjects for this subject
        result = await db_session.execute(
            select(TeacherSubject)
            .where(TeacherSubject.subject_id == subject.id)
            .where(TeacherSubject.is_active == True)
        )
        teacher_subjects = result.scalars().all()
        
        # Check if any teacher_subject has assignments
        has_assignments = False
        for teacher_subject in teacher_subjects:
            assignments_result = await db_session.execute(
                select(Assignment)
                .where(Assignment.teacher_subject_id == teacher_subject.id)
                .limit(1)
            )
            if assignments_result.scalar_one_or_none():
                has_assignments = True
                break
        
        if has_assignments:
            subjects_with_assignments.append(subject)
    
    if not subjects_with_assignments:
        await callback.message.edit_text(
            f"❌ <b>لا توجد وظائف متاحة</b>\n\n"
            f"التخصص: <b>{specialization.name}</b>\n\n"
            "لم يتم رفع أي وظائف للمواد الدراسية الخاصة بتخصصك بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Build inline keyboard with subjects that have assignments
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for subject in subjects_with_assignments:
        subject_name = subject.name
        if subject.code:
            subject_name = f"{subject_name} ({subject.code})"
        
        builder.add(InlineKeyboardButton(
            text=subject_name,
            callback_data=f"student_assignment_subject:{subject.id}"
        ))
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📚 <b>اختر المادة الدراسية:</b>\n\n"
        f"التخصص: <b>{specialization.name}</b>\n\n"
        "اختر المادة التي تريد تحميل وظائفها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("student_assignment_subject:"))
async def show_assignments_for_subject(callback: CallbackQuery, bot: Bot, db_session: AsyncSession, user: User):
    """Show assignments for selected subject and send them to student."""
    subject_id = int(callback.data.split(":")[1])
    
    # Verify subject belongs to student's specialization
    if not user.specialization_id:
        await callback.answer("❌ لم يتم تحديد التخصص الخاص بك.", show_alert=True)
        return
    
    subject_repo = SubjectRepository(db_session)
    subject = await subject_repo.get_by_id(subject_id)
    
    if not subject or subject.specialization_id != user.specialization_id:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Get all teacher_subjects for this subject
    result = await db_session.execute(
        select(TeacherSubject)
        .where(TeacherSubject.subject_id == subject_id)
        .where(TeacherSubject.is_active == True)
    )
    teacher_subjects = result.scalars().all()
    
    # Collect all assignments from all teachers for this subject
    all_assignments: List[Assignment] = []
    for teacher_subject in teacher_subjects:
        # Get assignments ordered by display_order
        assignments_result = await db_session.execute(
            select(Assignment)
            .where(Assignment.teacher_subject_id == teacher_subject.id)
            .order_by(Assignment.display_order.asc())
        )
        assignments = assignments_result.scalars().all()
        all_assignments.extend(assignments)
    
    if not all_assignments:
        await callback.message.edit_text(
            f"❌ <b>لا توجد وظائف متاحة</b>\n\n"
            f"المادة: <b>{subject.name}</b>\n\n"
            "لم يتم رفع أي وظائف لهذه المادة بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Send subject info
    subject_info = f"📝 <b>{subject.name}</b>"
    if subject.code:
        subject_info += f" ({subject.code})"
    subject_info += f"\n\n📁 عدد الوظائف: <b>{len(all_assignments)}</b> ملف\n\n"
    
    await callback.message.edit_text(
        subject_info + "⏳ جاري إرسال الوظائف...",
        parse_mode="HTML"
    )
    await callback.answer()
    
    # Send all assignment files
    sent_count = 0
    for idx, assignment in enumerate(all_assignments, 1):
        try:
            # Send file based on type
            if assignment.file_type == "document":
                await bot.send_document(
                    chat_id=user.telegram_id,
                    document=assignment.file_id,
                    caption=f"📄 الوظيفة {idx}/{len(all_assignments)}" + (f" - {assignment.file_name}" if assignment.file_name else "")
                )
            elif assignment.file_type == "photo":
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=assignment.file_id,
                    caption=f"🖼️ الوظيفة {idx}/{len(all_assignments)}"
                )
            elif assignment.file_type == "video":
                await bot.send_video(
                    chat_id=user.telegram_id,
                    video=assignment.file_id,
                    caption=f"🎥 الوظيفة {idx}/{len(all_assignments)}"
                )
            elif assignment.file_type == "audio":
                await bot.send_audio(
                    chat_id=user.telegram_id,
                    audio=assignment.file_id,
                    caption=f"🎵 الوظيفة {idx}/{len(all_assignments)}"
                )
            elif assignment.file_type == "voice":
                await bot.send_voice(
                    chat_id=user.telegram_id,
                    voice=assignment.file_id,
                    caption=f"🎤 الوظيفة {idx}/{len(all_assignments)}"
                )
            elif assignment.file_type == "video_note":
                await bot.send_video_note(
                    chat_id=user.telegram_id,
                    video_note=assignment.file_id
                )
            else:
                # Fallback: send as document
                await bot.send_document(
                    chat_id=user.telegram_id,
                    document=assignment.file_id,
                    caption=f"📄 الوظيفة {idx}/{len(all_assignments)}"
                )
            
            sent_count += 1
            
            # Small delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(0.5)
            
        except Exception as e:
            # Log error but continue sending other files
            print(f"Error sending assignment {assignment.id}: {e}")
            continue
    
    # Send completion message
    if sent_count > 0:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=f"✅ <b>تم إرسال {sent_count} من {len(all_assignments)} وظيفة</b>\n\n"
                 "يمكنك اختيار مادة أخرى أو العودة للقائمة.",
            parse_mode="HTML",
            reply_markup=get_e_learning_keyboard()
        )
    else:
        await bot.send_message(
            chat_id=user.telegram_id,
            text="❌ حدث خطأ أثناء إرسال الوظائف.\n\n"
                 "يرجى المحاولة مرة أخرى لاحقاً.",
            reply_markup=get_e_learning_keyboard()
        )


@router.callback_query(F.data == "assignment_upload_student")
async def show_upload_assignment_subjects(callback: CallbackQuery, db_session: AsyncSession, user: User):
    """Show subjects that have assignments for student to upload solution."""
    # Check if student has specialization
    if not user.specialization_id:
        await callback.answer("❌ لم يتم تحديد التخصص الخاص بك.", show_alert=True)
        return
    
    # Get student's specialization
    from repositories.specialization_repository import SpecializationRepository
    spec_repo = SpecializationRepository(db_session)
    specialization = await spec_repo.get_by_id(user.specialization_id)
    
    if not specialization:
        await callback.answer("❌ التخصص الخاص بك غير موجود في النظام.", show_alert=True)
        return
    
    # Get all active subjects for this specialization
    subject_repo = SubjectRepository(db_session)
    subjects = await subject_repo.get_by_specialization(user.specialization_id, active_only=True)
    
    if not subjects:
        await callback.message.edit_text(
            f"❌ لا توجد مواد دراسية متاحة لتخصص <b>{specialization.name}</b>.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Get all teacher_subjects for these subjects and check which ones have assignments
    subjects_with_assignments = []
    for subject in subjects:
        # Get all teacher_subjects for this subject
        result = await db_session.execute(
            select(TeacherSubject)
            .where(TeacherSubject.subject_id == subject.id)
            .where(TeacherSubject.is_active == True)
        )
        teacher_subjects = result.scalars().all()
        
        # Check if any teacher_subject has assignments
        has_assignments = False
        for teacher_subject in teacher_subjects:
            assignments_result = await db_session.execute(
                select(Assignment)
                .where(Assignment.teacher_subject_id == teacher_subject.id)
                .limit(1)
            )
            if assignments_result.scalar_one_or_none():
                has_assignments = True
                break
        
        if has_assignments:
            subjects_with_assignments.append(subject)
    
    if not subjects_with_assignments:
        await callback.message.edit_text(
            f"❌ <b>لا توجد وظائف متاحة</b>\n\n"
            f"التخصص: <b>{specialization.name}</b>\n\n"
            "لم يتم رفع أي وظائف للمواد الدراسية الخاصة بتخصصك بعد.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Build inline keyboard with subjects that have assignments
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for subject in subjects_with_assignments:
        subject_name = subject.name
        if subject.code:
            subject_name = f"{subject_name} ({subject.code})"
        
        builder.add(InlineKeyboardButton(
            text=subject_name,
            callback_data=f"student_upload_assignment_subject:{subject.id}"
        ))
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📚 <b>اختر المادة الدراسية:</b>\n\n"
        f"التخصص: <b>{specialization.name}</b>\n\n"
        "اختر المادة التي تريد رفع حل وظيفتها:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("student_upload_assignment_subject:"))
async def process_upload_assignment_subject(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, user: User):
    """Process subject selection and ask for assignment solution file."""
    subject_id = int(callback.data.split(":")[1])
    
    # Verify subject belongs to student's specialization
    if not user.specialization_id:
        await callback.answer("❌ لم يتم تحديد التخصص الخاص بك.", show_alert=True)
        return
    
    subject_repo = SubjectRepository(db_session)
    subject = await subject_repo.get_by_id(subject_id)
    
    if not subject or subject.specialization_id != user.specialization_id:
        await callback.answer("❌ هذه المادة غير متاحة لك.", show_alert=True)
        return
    
    # Verify that this subject has assignments
    result = await db_session.execute(
        select(TeacherSubject)
        .where(TeacherSubject.subject_id == subject_id)
        .where(TeacherSubject.is_active == True)
    )
    teacher_subjects = result.scalars().all()
    
    has_assignments = False
    for teacher_subject in teacher_subjects:
        assignments_result = await db_session.execute(
            select(Assignment)
            .where(Assignment.teacher_subject_id == teacher_subject.id)
            .limit(1)
        )
        if assignments_result.scalar_one_or_none():
            has_assignments = True
            break
    
    if not has_assignments:
        await callback.answer("❌ هذه المادة لا تحتوي على وظائف.", show_alert=True)
        return
    
    # Store subject info in state
    await state.update_data(
        subject_id=subject_id,
        subject_name=subject.name
    )
    
    await callback.message.edit_text(
        f"✅ تم اختيار المادة: <b>{subject.name}</b>\n\n"
        "📤 <b>الآن يمكنك رفع ملف حل الوظيفة:</b>\n\n"
        "• يمكنك إرسال <b>ملف واحد</b> (مستند، ملف مضغوط ZIP/RAR)\n"
        "• الملف يجب أن يحتوي على حل الوظيفة\n"
        "• بعد إرسال الملف، سيتم حفظه للتصحيح من قبل الأستاذ",
        parse_mode="HTML"
    )
    
    # Set state to wait for file
    await state.set_state(AssignmentUploadStates.waiting_for_assignment_file)
    await callback.answer()


@router.message(AssignmentUploadStates.waiting_for_assignment_file, F.document | F.photo)
async def process_assignment_solution_file(message: Message, state: FSMContext, db_session: AsyncSession, user: User):
    """Process uploaded assignment solution file."""
    
    data = await state.get_data()
    subject_id = data.get("subject_id")
    subject_name = data.get("subject_name", "المادة")
    
    if not subject_id:
        await message.answer("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")
        await state.clear()
        return
    
    file_info = None
    file_type = None
    
    # Handle document (preferred for assignments)
    if message.document:
        file_info = message.document
        file_type = "document"
    elif message.photo:
        # Get the largest photo
        file_info = message.photo[-1]
        file_type = "photo"
    else:
        await message.answer(
            "❌ يرجى إرسال ملف (مستند أو ملف مضغوط) كحل للوظيفة."
        )
        return
    
    # Get the first assignment for this subject (we'll link to the subject, not specific assignment)
    result = await db_session.execute(
        select(TeacherSubject)
        .where(TeacherSubject.subject_id == subject_id)
        .where(TeacherSubject.is_active == True)
        .limit(1)
    )
    teacher_subject = result.scalar_one_or_none()
    
    if not teacher_subject:
        await message.answer("❌ حدث خطأ في العثور على المادة.")
        await state.clear()
        return
    
    # Get first assignment for this teacher_subject
    assignment_result = await db_session.execute(
        select(Assignment)
        .where(Assignment.teacher_subject_id == teacher_subject.id)
        .order_by(Assignment.display_order.asc())
        .limit(1)
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        await message.answer("❌ لم يتم العثور على الوظيفة.")
        await state.clear()
        return
    
    # Extract file information
    file_id = file_info.file_id
    file_name = getattr(file_info, "file_name", None) or getattr(file_info, "file_unique_id", None)
    file_size = getattr(file_info, "file_size", None)
    
    # Check if student already submitted for this assignment
    existing_submission = await db_session.execute(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.student_id == user.id)
        .where(AssignmentSubmission.assignment_id == assignment.id)
    )
    existing = existing_submission.scalar_one_or_none()
    
    if existing:
        # Update existing submission
        existing.file_id = file_id
        existing.file_type = file_type
        existing.file_name = file_name
        existing.file_size = file_size
        await db_session.commit()
        
        await message.answer(
            f"✅ <b>تم تحديث حل الوظيفة بنجاح!</b>\n\n"
            f"📚 المادة: <b>{subject_name}</b>\n"
            f"📁 الملف: <b>{file_name or 'ملف'}</b>\n\n"
            "سيتم مراجعة الحل من قبل الأستاذ.",
            parse_mode="HTML",
            reply_markup=get_e_learning_keyboard()
        )
    else:
        # Create new submission
        submission = AssignmentSubmission(
            student_id=user.id,
            assignment_id=assignment.id,
            subject_id=subject_id,
            file_id=file_id,
            file_type=file_type,
            file_name=file_name,
            file_size=file_size
        )
        db_session.add(submission)
        await db_session.commit()
        
        await message.answer(
            f"✅ <b>تم رفع حل الوظيفة بنجاح!</b>\n\n"
            f"📚 المادة: <b>{subject_name}</b>\n"
            f"📁 الملف: <b>{file_name or 'ملف'}</b>\n\n"
            "سيتم مراجعة الحل من قبل الأستاذ.",
            parse_mode="HTML",
            reply_markup=get_e_learning_keyboard()
        )
    
    await state.clear()



