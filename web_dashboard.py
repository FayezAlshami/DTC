"""Web Dashboard for Bot Administration."""
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic
import secrets
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, String
from sqlalchemy.orm import selectinload
from jinja2 import Template
from database.base import AsyncSessionLocal
from database.models import User, Service, ServiceRequest, ServiceStatus, RequestStatus, Specialization
from repositories.service_repository import ServiceRepository
from repositories.request_repository import ServiceRequestRepository
from repositories.user_repository import UserRepository
from repositories.specialization_repository import SpecializationRepository
from config import config
import bcrypt
import os
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

app = FastAPI(title="DTC Job Bot Dashboard")
security = HTTPBasic()

# Mount static files directory
if not os.path.exists("static"):
    os.makedirs("static")
if not os.path.exists("static/images"):
    os.makedirs("static/images")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Session storage (in production, use Redis or database)
sessions = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_session(request: Request) -> Optional[str]:
    """Get session from cookie."""
    return request.cookies.get("session_id")


async def get_db():
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def require_auth(request: Request, db: AsyncSession = Depends(get_db)):
    """Require authentication."""
    session_id = get_session(request)
    
    if not session_id or session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return sessions[session_id]


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page."""
    with open("templates/login.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(error=None))


@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle login."""
    # Check credentials
    if email == config.WEB_DASHBOARD_EMAIL and password == config.WEB_DASHBOARD_PASSWORD:
        # Create session
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {"email": email, "authenticated": True}
        
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    
    # Also check database for admin users
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)
    
    if user and user.role.value == "admin":
        if await user_repo.verify_password(user, password):
            session_id = secrets.token_urlsafe(32)
            sessions[session_id] = {"email": email, "user_id": user.id, "authenticated": True}
            
            response = RedirectResponse(url="/dashboard", status_code=303)
            response.set_cookie(key="session_id", value=session_id, httponly=True)
            return response
    
    with open("templates/login.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(error="البريد الإلكتروني أو كلمة المرور غير صحيحة"))


@app.get("/logout")
async def logout(request: Request):
    """Handle logout."""
    session_id = get_session(request)
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="session_id")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Show dashboard."""
    # Get statistics
    service_repo = ServiceRepository(db)
    request_repo = ServiceRequestRepository(db)
    user_repo = UserRepository(db)
    
    # Get pending items - use string comparison to avoid enum case issues
    pending_services = await db.execute(
        select(Service)
        .options(selectinload(Service.provider))
        .where(Service.status == "pending")
        .order_by(Service.created_at.desc())
    )
    pending_services = pending_services.scalars().all()
    
    pending_requests = await db.execute(
        select(ServiceRequest)
        .options(selectinload(ServiceRequest.requester))
        .where(ServiceRequest.status == "pending")
        .order_by(ServiceRequest.created_at.desc())
    )
    pending_requests = pending_requests.scalars().all()
    
    # Get statistics
    all_services = await db.execute(select(Service))
    all_services = all_services.scalars().all()
    
    all_requests = await db.execute(select(ServiceRequest))
    all_requests = all_requests.scalars().all()
    
    all_users = await db.execute(select(User))
    all_users = all_users.scalars().all()
    
    stats = {
        "total_services": len(all_services),
        "pending_services": len(pending_services),
        "published_services": len([s for s in all_services if str(s.status) == str(ServiceStatus.PUBLISHED)]),
        "total_requests": len(all_requests),
        "pending_requests": len(pending_requests),
        "published_requests": len([r for r in all_requests if str(r.status) == str(RequestStatus.PUBLISHED)]),
        "total_users": len(all_users),
    }
    
    with open("templates/dashboard.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(
        session=session,
        stats=stats,
        pending_services=pending_services[:10],
        pending_requests=pending_requests[:10],
    ))


@app.get("/services", response_class=HTMLResponse)
async def services_page(
    request: Request,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None),
    specialization_filter: Optional[str] = Query(None)
):
    """Show services management page."""
    service_repo = ServiceRepository(db)
    
    # Build query with filters and eager load relationships
    query = select(Service).options(selectinload(Service.provider)).order_by(Service.created_at.desc())
    
    if status_filter and status_filter != "all":
        try:
            status_enum = ServiceStatus[status_filter.upper()]
            query = query.where(Service.status == status_enum)
        except (KeyError, AttributeError):
            pass
    
    if specialization_filter and specialization_filter != "all":
        query = query.where(Service.specialization.ilike(f"%{specialization_filter}%"))
    
    result = await db.execute(query)
    all_services = result.scalars().all()
    
    # Get unique specializations for filter dropdown
    specializations_query = select(Service.specialization).distinct()
    specializations_result = await db.execute(specializations_query)
    unique_specializations = sorted([s for s in specializations_result.scalars().all() if s])
    
    with open("templates/services.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(
        session=session,
        services=all_services,
        status_filter=status_filter or "all",
        specialization_filter=specialization_filter or "all",
        specializations=unique_specializations,
    ))


@app.get("/requests", response_class=HTMLResponse)
async def requests_page(
    request: Request,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Show requests management page."""
    request_repo = ServiceRequestRepository(db)
    all_requests = await request_repo.get_all_requests(limit=100)
    
    with open("templates/requests.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(
        session=session,
        requests=all_requests,
    ))


@app.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None)
):
    """Show users management page."""
    user_repo = UserRepository(db)
    
    if search:
        # Search users by name, email, or telegram_id
        search_term = f"%{search}%"
        query = select(User).where(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
                User.telegram_id.cast(String).ilike(search_term)
            )
        ).order_by(User.created_at.desc())
        result = await db.execute(query)
        all_users = result.scalars().all()
    else:
        all_users = await user_repo.get_all_users(limit=100)
    
    with open("templates/users.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(
        session=session,
        users=all_users,
        search_query=search or "",
    ))


@app.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_page(
    user_id: int,
    request: Request,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Show edit user page."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # Get specializations for dropdown
    from repositories.specialization_repository import SpecializationRepository
    spec_repo = SpecializationRepository(db)
    specializations = await spec_repo.get_all_active()
    
    with open("templates/edit_user.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(
        session=session,
        user=user,
        specializations=specializations,
    ))


@app.post("/api/users/{user_id}/update")
async def update_user(
    user_id: int,
    request: Request,
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    student_id: Optional[str] = Form(None),
    specialization: Optional[str] = Form(None),
    is_student: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update user information."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # Update fields if provided
    if full_name is not None:
        user.full_name = full_name.strip() if full_name.strip() else None  # type: ignore
    if email is not None:
        # Check if email already exists for another user
        existing = await user_repo.get_by_email(email.strip())
        if existing is not None and getattr(existing, 'id', None) != user_id:
            raise HTTPException(status_code=400, detail="البريد الإلكتروني مستخدم بالفعل")
        user.email = email.strip()  # type: ignore
    if phone_number is not None:
        user.phone_number = phone_number.strip() if phone_number.strip() else None  # type: ignore
    if student_id is not None:
        user.student_id = student_id.strip() if student_id.strip() else None  # type: ignore
    if specialization is not None:
        user.specialization = specialization.strip() if specialization.strip() else None  # type: ignore
    if is_student is not None:
        user.is_student = bool(is_student)  # type: ignore
    if is_active is not None:
        user.is_active = bool(is_active)  # type: ignore
    
    await user_repo.update(user)
    
    return {"status": "success", "message": "تم تحديث بيانات المستخدم بنجاح"}


@app.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(
    request: Request,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Show broadcast page."""
    user_repo = UserRepository(db)
    all_users = await user_repo.get_all_users(limit=1000)
    students = await user_repo.get_students(limit=1000)
    non_students = await user_repo.get_non_students(limit=1000)
    
    with open("templates/broadcast.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(
        session=session,
        total_users=len(all_users),
        total_students=len(students),
        total_non_students=len(non_students),
    ))


@app.post("/api/broadcast")
async def broadcast_message(
    request: Request,
    message: str = Form(...),
    target: str = Form(...),  # "all", "students", "non_students"
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Broadcast message to users."""
    bot = Bot(token=config.BOT_TOKEN)
    user_repo = UserRepository(db)
    
    # Get target users
    if target == "all":
        users = await user_repo.get_all_users(limit=10000)
    elif target == "students":
        users = await user_repo.get_students(limit=10000)
    elif target == "non_students":
        users = await user_repo.get_non_students(limit=10000)
    else:
        raise HTTPException(status_code=400, detail="Invalid target")
    
    # Filter active users only
    users = [u for u in users if bool(u.is_active)]
    
    success_count = 0
    failed_count = 0
    
    for user in users:
        try:
            telegram_id: int = int(user.telegram_id)  # type: ignore
            await bot.send_message(telegram_id, message)
            success_count += 1
        except (TelegramBadRequest, Exception) as e:
            failed_count += 1
            # If user blocked bot, mark as inactive
            if "blocked" in str(e).lower() or "chat not found" in str(e).lower():
                user.is_active = False  # type: ignore
                await user_repo.update(user)
    
    await bot.session.close()
    
    return {
        "status": "success",
        "message": f"تم إرسال الرسالة إلى {success_count} مستخدم",
        "success_count": success_count,
        "failed_count": failed_count
    }


@app.post("/api/ban_user/{user_id}")
async def ban_user(
    user_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Ban a user and delete their services if they are a student."""
    user_repo = UserRepository(db)
    service_repo = ServiceRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Ban user
    user.is_active = False  # type: ignore
    await user_repo.update(user)
    
    # If user is a student, delete all their services
    if bool(user.is_student):
        services = await service_repo.get_by_provider(user_id, limit=10000)
        deleted_count = 0
        bot = Bot(token=config.BOT_TOKEN)
        
        for service in services:
            # Delete from channel if published
            channel_msg_id = service.channel_message_id
            if channel_msg_id is not None and str(service.status) == "published":
                try:
                    msg_id: int = int(channel_msg_id)  # type: ignore
                    await bot.delete_message(config.SERVICES_CHANNEL_ID, msg_id)
                except Exception:
                    pass
            
            # Delete service from database
            await service_repo.delete(service)
            deleted_count += 1
        
        await bot.session.close()
        
        return {
            "status": "success",
            "message": f"تم حظر المستخدم وحذف {deleted_count} خدمة",
            "deleted_services": deleted_count
        }
    
    return {
        "status": "success",
        "message": "تم حظر المستخدم",
        "deleted_services": 0
    }


@app.post("/api/unban_user/{user_id}")
async def unban_user(
    user_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Unban a user."""
    user_repo = UserRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True  # type: ignore
    await user_repo.update(user)
    
    return {
        "status": "success",
        "message": "تم إلغاء حظر المستخدم"
    }


@app.post("/api/approve_service/{service_id}")
async def approve_service(
    service_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Approve a service (API endpoint)."""
    service_repo = ServiceRepository(db)
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if str(service.status) != "pending":
        raise HTTPException(status_code=400, detail="Service is not pending")
    
    service.status = ServiceStatus.PUBLISHED  # type: ignore
    await service_repo.update(service)
    
    return {"status": "success", "message": "Service approved"}


@app.post("/api/reject_service/{service_id}")
async def reject_service(
    service_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Reject a service (API endpoint)."""
    service_repo = ServiceRepository(db)
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if str(service.status) != "pending":
        raise HTTPException(status_code=400, detail="Service is not pending")
    
    service.status = ServiceStatus.REJECTED  # type: ignore
    await service_repo.update(service)
    
    return {"status": "success", "message": "Service rejected"}


@app.post("/api/approve_request/{request_id}")
async def approve_request(
    request_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Approve a request (API endpoint)."""
    request_repo = ServiceRequestRepository(db)
    request = await request_repo.get_by_id(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if str(request.status) != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    request.status = RequestStatus.PUBLISHED  # type: ignore
    await request_repo.update(request)
    
    return {"status": "success", "message": "Request approved"}


@app.post("/api/reject_request/{request_id}")
async def reject_request(
    request_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Reject a request (API endpoint)."""
    request_repo = ServiceRequestRepository(db)
    request = await request_repo.get_by_id(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if str(request.status) != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    request.status = RequestStatus.REJECTED  # type: ignore
    await request_repo.update(request)
    
    return {"status": "success", "message": "Request rejected"}


@app.get("/specializations", response_class=HTMLResponse)
async def specializations_page(
    request: Request,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Show specializations management page."""
    spec_repo = SpecializationRepository(db)
    all_specializations = await spec_repo.get_all()
    
    with open("templates/specializations.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(
        session=session,
        specializations=all_specializations,
    ))


@app.post("/api/specialization")
async def create_specialization(
    name: str = Form(...),
    display_order: int = Form(0),
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Create a new specialization."""
    spec_repo = SpecializationRepository(db)
    
    # Check if specialization already exists
    existing = await spec_repo.get_by_name(name)
    if existing:
        raise HTTPException(status_code=400, detail="الاختصاص موجود بالفعل")
    
    specialization = Specialization(
        name=name.strip(),
        display_order=display_order,
        is_active=True
    )
    await spec_repo.create(specialization)
    
    return {"status": "success", "message": "تم إضافة الاختصاص بنجاح"}


@app.post("/api/specialization/{spec_id}/toggle")
async def toggle_specialization(
    spec_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Toggle specialization active status."""
    spec_repo = SpecializationRepository(db)
    spec = await spec_repo.get_by_id(spec_id)
    
    if not spec:
        raise HTTPException(status_code=404, detail="الاختصاص غير موجود")
    
    is_active = getattr(spec, 'is_active', False)
    if bool(is_active):
        await spec_repo.deactivate(spec_id)
        return {"status": "success", "message": "تم تعطيل الاختصاص"}
    else:
        await spec_repo.activate(spec_id)
        return {"status": "success", "message": "تم تفعيل الاختصاص"}


@app.post("/api/specialization/{spec_id}/update")
async def update_specialization(
    spec_id: int,
    name: str = Form(...),
    display_order: int = Form(0),
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update specialization."""
    spec_repo = SpecializationRepository(db)
    spec = await spec_repo.get_by_id(spec_id)
    
    if not spec:
        raise HTTPException(status_code=404, detail="الاختصاص غير موجود")
    
    # Check if name already exists for another specialization
    existing = await spec_repo.get_by_name(name.strip())
    if existing is not None and getattr(existing, 'id', None) != spec_id:
        raise HTTPException(status_code=400, detail="اسم الاختصاص مستخدم بالفعل")
    
    spec.name = name.strip()  # type: ignore
    spec.display_order = display_order  # type: ignore
    await spec_repo.update(spec)
    
    return {"status": "success", "message": "تم تحديث الاختصاص بنجاح"}


@app.post("/api/specialization/{spec_id}/delete")
async def delete_specialization(
    spec_id: int,
    session: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete specialization."""
    spec_repo = SpecializationRepository(db)
    spec = await spec_repo.get_by_id(spec_id)
    
    if not spec:
        raise HTTPException(status_code=404, detail="الاختصاص غير موجود")
    
    # Deactivate instead of delete to preserve data integrity
    await spec_repo.deactivate(spec_id)
    
    return {"status": "success", "message": "تم حذف الاختصاص بنجاح"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.WEB_DASHBOARD_PORT)

