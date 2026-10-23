from __future__ import annotations

import asyncio
import logging
import os
import io
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from typing import Annotated
from collections import defaultdict

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from twilio.rest import Client
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from database import AsyncSessionLocal, get_db, init_database
from models import (
    AttendanceStatus,
    DailyConsumption,
    MealAttendance,
    MealType,
    Menu,
    MenuItem,
    NotificationLog,
    Student,
    User,
    UserRole,
    UnitType,
)
from schemas import (
    AnalyticsResponse,
    AttendanceResponse,
    AttendanceScan,
    AttendanceUpdate,
    ConsumptionCreate,
    ConsumptionResponse,
    DashboardMealSummary,
    DashboardResponse,
    MealMenuCreate,
    MenuCreate,
    MenuItemResponse,
    MenuResponse,
    MessageResponse,
    NotificationResponse,
    ReportRequest,
    StudentCreate,
    StudentHistoryResponse,
    StudentMealHistory,
    StudentResponse,
    UserResponse,
    WasteRecord,
)


logger = logging.getLogger("smart-mess")


class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield


app = FastAPI(
    title="Smart Mess Management System",
    description=(
        "Smart Mess Management System for hostel "
        "student attendance, menu, consumption, waste "
        "analytics and notifications."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTHENTICATION
# ============================================================


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    username: str,
    role: str,
) -> str:

    expires = datetime.utcnow() + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": username,
        "role": role,
        "exp": expires,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:

    result = await db.execute(
        select(User).where(
            User.username == username
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not verify_password(
        password,
        user.hashed_password,
    ):
        return None

    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        username = payload.get("sub")

        if not username:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(
            User.username == username
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def require_warden(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:

    if current_user.role != UserRole.WARDEN:
        raise HTTPException(
            status_code=403,
            detail="Warden access required.",
        )

    return current_user


async def require_staff(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:

    if current_user.role not in (
        UserRole.WARDEN,
        UserRole.OPERATOR,
    ):
        raise HTTPException(
            status_code=403,
            detail="Staff access required.",
        )

    return current_user


# ============================================================
# HELPERS
# ============================================================


def menu_to_response(menu: Menu) -> MenuResponse:

    sorted_items = sorted(
        menu.items,
        key=lambda item: (
            item.meal.value,
            item.id,
        ),
    )

    return MenuResponse(
        id=menu.id,
        date=menu.date,
        items=[
            MenuItemResponse(
                id=item.id,
                meal=item.meal,
                item_name=item.item_name,
                planned_servings=item.planned_servings,
                unit=item.unit,
            )
            for item in sorted_items
        ],
    )


async def get_menu_by_date(
    db: AsyncSession,
    menu_date: date,
) -> Menu | None:

    result = await db.execute(
        select(Menu)
        .options(
            selectinload(Menu.items)
        )
        .where(
            Menu.date == menu_date
        )
    )

    return result.scalar_one_or_none()


async def send_menu_notification(
    menu_date: date,
    menu_items: list[MenuItem],
):
    grouped: dict[str, list[str]] = {
        "Breakfast": [],
        "Lunch": [],
        "Dinner": [],
    }

    meal_names = {
        MealType.BREAKFAST: "Breakfast",
        MealType.LUNCH: "Lunch",
        MealType.DINNER: "Dinner",
    }

    for item in menu_items:
        grouped[
            meal_names[item.meal]
        ].append(
            item.item_name
        )

    message_body = (
        f"🍽️ Smart Mess Menu - {menu_date}\n\n"
        f"🌅 Breakfast: "
        f"{', '.join(grouped['Breakfast']) or 'Not available'}\n\n"
        f"☀️ Lunch: "
        f"{', '.join(grouped['Lunch']) or 'Not available'}\n\n"
        f"🌙 Dinner: "
        f"{', '.join(grouped['Dinner']) or 'Not available'}\n\n"
        "Please check the mess schedule and plan your meals accordingly."
    )

    async with AsyncSessionLocal() as db:

        student_result = await db.execute(
            select(Student).where(
                Student.notification_enabled == True,
                Student.phone_number.is_not(None),
                Student.phone_number != "",
            )
        )

        students = student_result.scalars().all()

        recipient_count = len(students)

        for student in students:
            logger.info(
                "FASTAPI DEMO NOTIFICATION -> %s: %s",
                student.name,
                message_body,
            )

        notification = NotificationLog(
            notification_type="menu",
            title=f"Menu for {menu_date}",
            message=message_body,
            recipient_count=recipient_count,
            status="processed",
        )

        db.add(notification)

        await db.commit()

        logger.info(
            "Menu notification processed for %s students.",
            recipient_count,
        )


# ============================================================
# BASIC
# ============================================================


@app.get("/")
async def root():
    return {
        "message": "Smart Mess Management System API",
        "version": "2.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected",
    }


# ============================================================
# AUTH ROUTES
# ============================================================


@app.post("/auth/login")
async def login(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
):
    user = await authenticate_user(
        db,
        form_data.username,
        form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password.",
        )

    token = create_access_token(
        user.username,
        user.role.value,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user.username,
            "role": user.role.value,
        },
    }


@app.get(
    "/auth/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
):
    return current_user


# ============================================================
# STUDENTS
# ============================================================


@app.get(
    "/students",
    response_model=list[StudentResponse],
)
async def get_students(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
):
    query = select(Student).order_by(
        Student.student_code,
        Student.id,
    )

    if search:
        pattern = f"%{search.strip()}%"

        query = query.where(
            or_(
                Student.name.ilike(pattern),
                Student.roll_number.ilike(pattern),
                Student.student_code.ilike(pattern),
            )
        )

    result = await db.execute(query)

    return result.scalars().all()


@app.post(
    "/students",
    response_model=StudentResponse,
)
async def create_student(
    student_data: StudentCreate,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_warden),
    ],
):

    existing = await db.execute(
        select(Student).where(
            Student.roll_number
            == student_data.roll_number
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Roll number already exists.",
        )

    student_code = (
        student_data.student_code
        or f"SM{1000 + int(datetime.utcnow().timestamp()) % 9000}"
    )

    qr_token = f"SMQR-{student_code}-{os.urandom(8).hex()}"

    student = Student(
        name=student_data.name,
        roll_number=student_data.roll_number,
        phone_number=student_data.phone_number,
        student_code=student_code,
        department=student_data.department,
        year=student_data.year,
        block=student_data.block,
        room_number=student_data.room_number,
        qr_token=qr_token,
        is_present_today=True,
    )

    db.add(student)

    await db.commit()
    await db.refresh(student)

    return student


@app.get(
    "/students/{student_id}",
    response_model=StudentHistoryResponse,
)
async def get_student_profile(
    student_id: int,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    student_result = await db.execute(
        select(Student).where(
            Student.id == student_id
        )
    )

    student = student_result.scalar_one_or_none()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    attendance_result = await db.execute(
        select(MealAttendance)
        .where(
            MealAttendance.student_id
            == student_id
        )
        .order_by(
            MealAttendance.date.desc(),
            MealAttendance.meal,
        )
    )

    records = attendance_result.scalars().all()

    history = [
        StudentMealHistory(
            date=record.date,
            meal=record.meal,
            time=record.scan_time,
            status=record.status,
        )
        for record in records
    ]

    total_meals = len(records)

    attended = sum(
        1
        for record in records
        if record.status
        == AttendanceStatus.PRESENT
    )

    skipped = sum(
        1
        for record in records
        if record.status
        == AttendanceStatus.SKIPPED
    )

    return StudentHistoryResponse(
        student=student,
        total_meals=total_meals,
        attended=attended,
        skipped=skipped,
        history=history,
    )


# ============================================================
# ATTENDANCE / QR SCANNING
# ============================================================


@app.post(
    "/attendance/scan",
    response_model=AttendanceResponse,
)
async def scan_student(
    scan: AttendanceScan,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    identifier = scan.student_identifier.strip()

    result = await db.execute(
        select(Student).where(
            or_(
                Student.student_code == identifier,
                Student.qr_token == identifier,
                Student.roll_number == identifier,
            )
        )
    )

    student = result.scalar_one_or_none()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student QR/ID not found.",
        )

    today = date.today()

    existing_result = await db.execute(
        select(MealAttendance).where(
            MealAttendance.student_id
            == student.id,
            MealAttendance.date == today,
            MealAttendance.meal
            == scan.meal,
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing:

        existing.status = AttendanceStatus.PRESENT
        existing.scan_time = datetime.now()

        await db.commit()
        await db.refresh(existing)

        return existing

    attendance = MealAttendance(
        student_id=student.id,
        date=today,
        meal=scan.meal,
        status=AttendanceStatus.PRESENT,
        scan_time=datetime.now(),
    )

    db.add(attendance)

    await db.commit()
    await db.refresh(attendance)

    return attendance



@app.post(
    "/attendance/simulate"
)
async def simulate_attendance(
    count: int,
    meal: MealType,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    if count < 1:
        raise HTTPException(
            status_code=400,
            detail="Student count must be at least 1.",
        )

    if count > 212:
        raise HTTPException(
            status_code=400,
            detail="Student count cannot exceed the registered student count.",
        )

    today = date.today()

    student_result = await db.execute(
        select(Student)
        .order_by(Student.id)
        .limit(count)
    )

    students = student_result.scalars().all()

    if not students:
        raise HTTPException(
            status_code=404,
            detail="No registered students found.",
        )

    student_ids = [student.id for student in students]

    existing_result = await db.execute(
        select(MealAttendance).where(
            MealAttendance.student_id.in_(student_ids),
            MealAttendance.date == today,
            MealAttendance.meal == meal,
        )
    )

    existing_records = {
        record.student_id: record
        for record in existing_result.scalars().all()
    }

    added_count = 0

    for student in students:

        if student.id in existing_records:
            existing_records[student.id].status = AttendanceStatus.PRESENT
            existing_records[student.id].scan_time = datetime.now()

        else:
            attendance = MealAttendance(
                student_id=student.id,
                date=today,
                meal=meal,
                status=AttendanceStatus.PRESENT,
                scan_time=datetime.now(),
            )

            db.add(attendance)
            added_count += 1

    await db.commit()

    return {
        "status": "success",
        "message": f"Attendance simulated for {len(students)} existing students.",
        "student_count": len(students),
        "new_records": added_count,
        "meal": meal.value,
        "date": str(today),
    }

@app.get(
    "/attendance/today"
)
async def get_today_attendance(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    today = date.today()

    result = await db.execute(
        select(
            MealAttendance,
            Student.name,
            Student.student_code,
        )
        .join(
            Student,
            Student.id == MealAttendance.student_id,
        )
        .where(
            MealAttendance.date == today,
            MealAttendance.status == AttendanceStatus.PRESENT,
        )
        .order_by(
            MealAttendance.meal,
            MealAttendance.scan_time,
        )
    )

    rows = result.all()

    return [
        {
            "student_id": attendance.student_id,
            "student_name": student_name,
            "student_code": student_code,
            "meal": attendance.meal.value,
            "status": attendance.status.value,
            "scan_time": (
                attendance.scan_time.isoformat()
                if attendance.scan_time
                else None
            ),
        }
        for attendance, student_name, student_code in rows
    ]



@app.get(
    "/attendance/{student_id}",
    response_model=list[AttendanceResponse],
)
async def get_student_attendance(
    student_id: int,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    result = await db.execute(
        select(MealAttendance)
        .where(
            MealAttendance.student_id
            == student_id
        )
        .order_by(
            MealAttendance.date.desc()
        )
    )

    return result.scalars().all()


# ============================================================
# MENUS
# ============================================================


@app.get(
    "/menus",
    response_model=list[MenuResponse],
)
async def get_menus(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
    from_date: date | None = None,
    to_date: date | None = None,
    menu_date: date | None = Query(
        default=None,
        alias="date",
    ),
):
    query = (
        select(Menu)
        .options(
            selectinload(Menu.items)
        )
        .order_by(
            Menu.date.desc()
        )
    )

    if from_date:
        query = query.where(
            Menu.date >= from_date
        )

    if to_date:
        query = query.where(
            Menu.date <= to_date
        )

    if menu_date:
        query = query.where(
            Menu.date == menu_date
        )

    result = await db.execute(query)

    menus = result.scalars().all()

    return [
        menu_to_response(menu)
        for menu in menus
    ]


@app.get(
    "/menus/today",
    response_model=MenuResponse | None,
)
async def get_today_menu(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    menu = await get_menu_by_date(
        db,
        date.today(),
    )

    if menu is None:
        return None

    return menu_to_response(menu)


@app.post(
    "/menus",
    response_model=MenuResponse,
)
async def create_menu(
    menu_data: MenuCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    if menu_data.date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Menu date cannot be in the past.",
        )

    existing_result = await db.execute(
        select(Menu).where(
            Menu.date == menu_data.date
        )
    )

    existing_menu = existing_result.scalar_one_or_none()

    if existing_menu:

        existing_menu.breakfast = ""
        existing_menu.lunch = ""
        existing_menu.dinner = ""

        await db.flush()

        old_items_result = await db.execute(
            select(MenuItem).where(
                MenuItem.menu_id
                == existing_menu.id
            )
        )

        old_items = old_items_result.scalars().all()

        for item in old_items:
            await db.delete(item)

        menu = existing_menu

    else:

        menu = Menu(
            date=menu_data.date,
            breakfast="",
            lunch="",
            dinner="",
        )

        db.add(menu)

        await db.flush()

    meal_text: dict[MealType, list[str]] = {
        MealType.BREAKFAST: [],
        MealType.LUNCH: [],
        MealType.DINNER: [],
    }

    for meal_data in menu_data.meals:

        for item_data in meal_data.items:

            menu_item = MenuItem(
                menu_id=menu.id,
                meal=meal_data.meal,
                item_name=item_data.item_name,
                planned_servings=item_data.planned_servings,
                unit=item_data.unit,
            )

            db.add(menu_item)

            meal_text[
                meal_data.meal
            ].append(
                item_data.item_name
            )

    menu.breakfast = ", ".join(
        meal_text[MealType.BREAKFAST]
    )

    menu.lunch = ", ".join(
        meal_text[MealType.LUNCH]
    )

    menu.dinner = ", ".join(
        meal_text[MealType.DINNER]
    )

    await db.commit()

    menu = await get_menu_by_date(
        db,
        menu_data.date,
    )

    if menu is None:
        raise HTTPException(
            status_code=500,
            detail="Menu could not be loaded after saving.",
        )

    background_tasks.add_task(
        send_menu_notification,
        menu.date,
        list(menu.items),
    )

    return menu_to_response(menu)


@app.post(
    "/menus/{menu_date}/send-notification",
)
async def send_menu_notification_endpoint(
    menu_date: date,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    menu = await get_menu_by_date(
        db,
        menu_date,
    )

    if menu is None:
        raise HTTPException(
            status_code=404,
            detail="No menu found for this date.",
        )

    await send_menu_notification(
        menu.date,
        list(menu.items),
    )

    student_result = await db.execute(
        select(Student).where(
            Student.notification_enabled == True,
            Student.phone_number.is_not(None),
            Student.phone_number != "",
        )
    )

    recipient_count = len(
        student_result.scalars().all()
    )

    return {
        "status": "processed",
        "message": (
            "Menu notification processed successfully "
            "for eligible registered students."
        ),
        "recipient_count": recipient_count,
        "date": str(menu_date),
    }


# ============================================================
# CONSUMPTION
# ============================================================


@app.post(
    "/consumption",
    response_model=ConsumptionResponse,
)
async def create_consumption(
    consumption_data: ConsumptionCreate,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):

    if (
        consumption_data.served_kg
        > consumption_data.prepared_kg
    ):
        raise HTTPException(
            status_code=400,
            detail="Served quantity cannot exceed prepared quantity.",
        )

    menu = await get_menu_by_date(
        db,
        consumption_data.date,
    )

    if menu is None:
        raise HTTPException(
            status_code=404,
            detail="No menu exists for this date.",
        )

    item_result = await db.execute(
        select(MenuItem).where(
            MenuItem.menu_id == menu.id,
            MenuItem.meal
            == consumption_data.meal,
            func.lower(MenuItem.item_name)
            == consumption_data.item_name.lower(),
        )
    )

    menu_item = item_result.scalar_one_or_none()

    if menu_item is None:
        raise HTTPException(
            status_code=404,
            detail="Menu item not found for the selected meal.",
        )

    if menu_item.unit == UnitType.COUNT:
        if (
            not consumption_data.prepared_kg.is_integer()
            or not consumption_data.served_kg.is_integer()
        ):
            raise HTTPException(
                status_code=400,
                detail="Count-based items must use whole-number quantities.",
            )

    waste = (
        consumption_data.prepared_kg
        - consumption_data.served_kg
    )

    existing_result = await db.execute(
        select(DailyConsumption).where(
            DailyConsumption.date
            == consumption_data.date,
            DailyConsumption.menu_item_id
            == menu_item.id,
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing:

        existing.prepared_kg = (
            consumption_data.prepared_kg
        )

        existing.served_kg = (
            consumption_data.served_kg
        )

        existing.waste_kg = waste

        existing.item_name = menu_item.item_name
        existing.meal = menu_item.meal
        existing.unit = menu_item.unit

        await db.commit()
        await db.refresh(existing)

        return existing

    consumption = DailyConsumption(
        date=consumption_data.date,
        item_name=menu_item.item_name,
        prepared_kg=consumption_data.prepared_kg,
        served_kg=consumption_data.served_kg,
        waste_kg=waste,
        unit=menu_item.unit,
        meal=menu_item.meal,
        menu_item_id=menu_item.id,
    )

    db.add(consumption)

    await db.commit()
    await db.refresh(consumption)

    return consumption


@app.get(
    "/consumption",
    response_model=list[ConsumptionResponse],
)
async def get_consumption(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
    record_date: date | None = None,
):
    query = select(
        DailyConsumption
    ).order_by(
        DailyConsumption.date.desc(),
        DailyConsumption.id.desc(),
    )

    if record_date:
        query = query.where(
            DailyConsumption.date
            == record_date
        )

    result = await db.execute(query)

    return result.scalars().all()


# ============================================================
# WASTE RECORD
# ============================================================


@app.get(
    "/waste",
    response_model=list[WasteRecord],
)
async def get_waste_records(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
    record_date: date | None = None,
):
    query = select(
        DailyConsumption
    ).order_by(
        DailyConsumption.date.desc(),
        DailyConsumption.id.desc(),
    )

    if record_date:
        query = query.where(
            DailyConsumption.date
            == record_date
        )

    result = await db.execute(query)

    records = result.scalars().all()

    return [
        WasteRecord(
            date=record.date,
            meal=record.meal,
            item_name=record.item_name,
            prepared_kg=record.prepared_kg,
            served_kg=record.served_kg,
            waste_kg=record.waste_kg,
            unit=record.unit,
        )
        for record in records
    ]


@app.get(
    "/waste/today-summary"
)
async def today_waste_summary(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    result = await db.execute(
        select(
            DailyConsumption.unit,
            func.coalesce(
                func.sum(
                    DailyConsumption.prepared_kg
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    DailyConsumption.served_kg
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    DailyConsumption.waste_kg
                ),
                0,
            ),
        )
        .where(
            DailyConsumption.date == today
        )
        .group_by(
            DailyConsumption.unit
        )
    )

    prepared_kg = 0.0
    served_kg = 0.0
    waste_kg = 0.0

    prepared_count = 0.0
    served_count = 0.0
    waste_count = 0.0

    for unit, prepared, served, waste in result.all():
        prepared_value = float(prepared or 0)
        served_value = float(served or 0)
        waste_value = float(waste or 0)

        if unit == UnitType.COUNT:
            prepared_count += prepared_value
            served_count += served_value
            waste_count += waste_value
        else:
            prepared_kg += prepared_value
            served_kg += served_value
            waste_kg += waste_value

    kg_percentage = (
        waste_kg / prepared_kg * 100
        if prepared_kg > 0
        else 0
    )

    count_percentage = (
        waste_count / prepared_count * 100
        if prepared_count > 0
        else 0
    )

    return {
        "date": today,

        "prepared_kg": round(prepared_kg, 2),
        "served_kg": round(served_kg, 2),
        "waste_kg": round(waste_kg, 2),
        "waste_percentage_kg": round(
            kg_percentage,
            2,
        ),

        "prepared_count": round(prepared_count, 2),
        "served_count": round(served_count, 2),
        "waste_count": round(waste_count, 2),
        "waste_percentage_count": round(
            count_percentage,
            2,
        ),
    }


# ============================================================
# DASHBOARD
# ============================================================


@app.get(
    "/dashboard",
    response_model=DashboardResponse,
)
async def dashboard(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    today = date.today()

    student_count_result = await db.execute(
        select(func.count(Student.id))
    )
    total_students = student_count_result.scalar() or 0

    menu = await get_menu_by_date(db, today)

    attendance_summaries = []

    for meal in MealType:
        attended_result = await db.execute(
            select(func.count(MealAttendance.id)).where(
                MealAttendance.date == today,
                MealAttendance.meal == meal,
                MealAttendance.status == AttendanceStatus.PRESENT,
            )
        )
        attended = attended_result.scalar() or 0

        skipped_result = await db.execute(
            select(func.count(MealAttendance.id)).where(
                MealAttendance.date == today,
                MealAttendance.meal == meal,
                MealAttendance.status == AttendanceStatus.SKIPPED,
            )
        )
        skipped = skipped_result.scalar() or 0

        not_yet_attended = max(
            0,
            total_students - attended - skipped,
        )

        attendance_summaries.append(
            DashboardMealSummary(
                meal=meal,
                attended=attended,
                not_yet_attended=not_yet_attended,
                skipped=skipped,
                total_students=total_students,
            )
        )

    present_students_result = await db.execute(
        select(
            func.count(func.distinct(MealAttendance.student_id))
        ).where(
            MealAttendance.date == today,
            MealAttendance.status == AttendanceStatus.PRESENT,
        )
    )
    present_students = present_students_result.scalar() or 0

    absent_students = max(
        0,
        total_students - present_students,
    )

    consumption_result = await db.execute(
        select(DailyConsumption).where(
            DailyConsumption.date == today
        )
    )

    today_consumption_records = consumption_result.scalars().all()

    consumption_count = len(today_consumption_records)

    total_prepared = sum(
        float(record.prepared_kg)
        for record in today_consumption_records
        if record.unit == UnitType.KG
    )

    total_served = sum(
        float(record.served_kg)
        for record in today_consumption_records
        if record.unit == UnitType.KG
    )

    total_waste = sum(
        float(record.waste_kg)
        for record in today_consumption_records
        if record.unit == UnitType.KG
    )

    total_prepared_count = sum(
        float(record.prepared_kg)
        for record in today_consumption_records
        if record.unit == UnitType.COUNT
    )

    total_served_count = sum(
        float(record.served_kg)
        for record in today_consumption_records
        if record.unit == UnitType.COUNT
    )

    total_waste_count = sum(
        float(record.waste_kg)
        for record in today_consumption_records
        if record.unit == UnitType.COUNT
    )

    today_waste_percentage = (
        (total_waste / total_prepared) * 100
        if total_prepared > 0
        else 0
    )

    today_count_waste_percentage = (
        (total_waste_count / total_prepared_count) * 100
        if total_prepared_count > 0
        else 0
    )

    menu_response = (
        menu_to_response(menu)
        if menu
        else None
    )

    menu_count = (
        len(menu_response.items)
        if menu_response
        else 0
    )

    user_response = UserResponse.model_validate(
        current_user
    )

    return DashboardResponse(
        today=today,
        user=user_response,
        menu=menu_response,
        today_menu=menu_response,
        attendance=attendance_summaries,
        total_students=total_students,
        present_students=present_students,
        absent_students=absent_students,
        menu_count=menu_count,
        consumption_count=consumption_count,
        total_prepared_kg=round(total_prepared, 2),
        total_served_kg=round(total_served, 2),
        total_waste_kg=round(total_waste, 2),
        today_waste_percentage=round(
            today_waste_percentage,
            2,
        ),
        total_prepared_count=round(total_prepared_count, 2),
        total_served_count=round(total_served_count, 2),
        total_waste_count=round(total_waste_count, 2),
        today_count_waste_percentage=round(
            today_count_waste_percentage,
            2,
        ),
    )


# ============================================================
# ATTENDANCE STATUS FINALIZATION
# ============================================================


@app.post(
    "/attendance/finalize/{meal}"
)
async def finalize_meal_attendance(
    meal: MealType,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    today = date.today()

    student_result = await db.execute(
        select(Student)
    )

    students = student_result.scalars().all()

    created = 0

    for student in students:

        existing_result = await db.execute(
            select(MealAttendance).where(
                MealAttendance.student_id
                == student.id,
                MealAttendance.date
                == today,
                MealAttendance.meal
                == meal,
            )
        )

        existing = (
            existing_result.scalar_one_or_none()
        )

        if existing is None:

            db.add(
                MealAttendance(
                    student_id=student.id,
                    date=today,
                    meal=meal,
                    status=AttendanceStatus.SKIPPED,
                    scan_time=None,
                )
            )

            created += 1

    await db.commit()

    return {
        "message": "Meal attendance finalized.",
        "date": today,
        "meal": meal.value,
        "skipped_records_created": created,
    }


# ============================================================
# ANALYTICS
# ============================================================



@app.get("/analytics")
async def get_analytics(
    from_date: date | None = None,
    to_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="From date cannot be after to date.",
        )

    query = select(DailyConsumption)

    if from_date:
        query = query.where(
            DailyConsumption.date >= from_date
        )

    if to_date:
        query = query.where(
            DailyConsumption.date <= to_date
        )

    query = query.order_by(
        DailyConsumption.date,
        DailyConsumption.id,
    )

    result = await db.execute(query)
    records = result.scalars().all()

    # ========================================================
    # TOTALS — KEEP KG AND COUNT COMPLETELY SEPARATE
    # ========================================================

    total_prepared_kg = sum(
        float(record.prepared_kg)
        for record in records
        if record.unit == UnitType.KG
    )

    total_served_kg = sum(
        float(record.served_kg)
        for record in records
        if record.unit == UnitType.KG
    )

    total_waste_kg = sum(
        float(record.waste_kg)
        for record in records
        if record.unit == UnitType.KG
    )

    total_prepared_count = sum(
        float(record.prepared_kg)
        for record in records
        if record.unit == UnitType.COUNT
    )

    total_served_count = sum(
        float(record.served_kg)
        for record in records
        if record.unit == UnitType.COUNT
    )

    total_waste_count = sum(
        float(record.waste_kg)
        for record in records
        if record.unit == UnitType.COUNT
    )

    waste_percentage_kg = (
        (total_waste_kg / total_prepared_kg) * 100
        if total_prepared_kg > 0
        else 0
    )

    waste_percentage_count = (
        (total_waste_count / total_prepared_count) * 100
        if total_prepared_count > 0
        else 0
    )

    # ========================================================
    # ITEM-WISE WASTE
    # ========================================================

    item_data = defaultdict(
        lambda: {
            "unit": UnitType.KG,
            "prepared": 0.0,
            "served": 0.0,
            "waste": 0.0,
        }
    )

    for record in records:
        item_key = (
            record.item_name,
            record.unit.value,
        )

        if item_key not in item_data:
            item_data[item_key] = {
                "unit": record.unit,
                "prepared": 0.0,
                "served": 0.0,
                "waste": 0.0,
            }

        item_data[item_key]["prepared"] += float(
            record.prepared_kg
        )
        item_data[item_key]["served"] += float(
            record.served_kg
        )
        item_data[item_key]["waste"] += float(
            record.waste_kg
        )

    item_waste = []

    for (item_name, unit_name), values in item_data.items():
        prepared = values["prepared"]
        served = values["served"]
        waste = values["waste"]

        percentage = (
            (waste / prepared) * 100
            if prepared > 0
            else 0
        )

        item_waste.append(
            {
                "item_name": item_name,
                "unit": unit_name,
                "prepared_kg": round(prepared, 2)
                if unit_name == "kg"
                else 0,
                "served_kg": round(served, 2)
                if unit_name == "kg"
                else 0,
                "waste_kg": round(waste, 2)
                if unit_name == "kg"
                else 0,
                "prepared_count": round(prepared, 2)
                if unit_name == "count"
                else 0,
                "served_count": round(served, 2)
                if unit_name == "count"
                else 0,
                "waste_count": round(waste, 2)
                if unit_name == "count"
                else 0,
                "waste_percentage": round(
                    percentage,
                    2,
                ),
            }
        )

    item_waste.sort(
        key=lambda x: x["waste_percentage"],
        reverse=True,
    )

    # ========================================================
    # DAILY TRENDS
    # ========================================================

    daily_data = defaultdict(
        lambda: {
            "kg": {
                "prepared": 0.0,
                "served": 0.0,
                "waste": 0.0,
            },
            "count": {
                "prepared": 0.0,
                "served": 0.0,
                "waste": 0.0,
            },
        }
    )

    for record in records:
        unit_name = record.unit.value

        daily_data[str(record.date)][unit_name]["prepared"] += float(
            record.prepared_kg
        )
        daily_data[str(record.date)][unit_name]["served"] += float(
            record.served_kg
        )
        daily_data[str(record.date)][unit_name]["waste"] += float(
            record.waste_kg
        )

    daily_trends = []

    for day, values in sorted(daily_data.items()):
        kg = values["kg"]
        count = values["count"]

        kg_percentage = (
            (kg["waste"] / kg["prepared"]) * 100
            if kg["prepared"] > 0
            else 0
        )

        count_percentage = (
            (count["waste"] / count["prepared"]) * 100
            if count["prepared"] > 0
            else 0
        )

        daily_trends.append(
            {
                "date": day,

                "prepared_kg": round(
                    kg["prepared"],
                    2,
                ),
                "served_kg": round(
                    kg["served"],
                    2,
                ),
                "waste_kg": round(
                    kg["waste"],
                    2,
                ),
                "waste_percentage": round(
                    kg_percentage,
                    2,
                ),

                "prepared_count": round(
                    count["prepared"],
                    2,
                ),
                "served_count": round(
                    count["served"],
                    2,
                ),
                "waste_count": round(
                    count["waste"],
                    2,
                ),
                "count_waste_percentage": round(
                    count_percentage,
                    2,
                ),
            }
        )

    # ========================================================
    # MEAL-WISE WASTE
    # ========================================================

    meal_data = defaultdict(
        lambda: {
            "kg": {
                "prepared": 0.0,
                "served": 0.0,
                "waste": 0.0,
            },
            "count": {
                "prepared": 0.0,
                "served": 0.0,
                "waste": 0.0,
            },
        }
    )

    for record in records:
        meal_name = (
            record.meal.value
            if record.meal is not None
            else "unknown"
        )

        unit_name = record.unit.value

        meal_data[meal_name][unit_name]["prepared"] += float(
            record.prepared_kg
        )
        meal_data[meal_name][unit_name]["served"] += float(
            record.served_kg
        )
        meal_data[meal_name][unit_name]["waste"] += float(
            record.waste_kg
        )

    meal_waste = []

    for meal_name, values in sorted(meal_data.items()):
        kg = values["kg"]
        count = values["count"]

        kg_percentage = (
            (kg["waste"] / kg["prepared"]) * 100
            if kg["prepared"] > 0
            else 0
        )

        count_percentage = (
            (count["waste"] / count["prepared"]) * 100
            if count["prepared"] > 0
            else 0
        )

        meal_waste.append(
            {
                "meal": meal_name,

                "prepared_kg": round(
                    kg["prepared"],
                    2,
                ),
                "served_kg": round(
                    kg["served"],
                    2,
                ),
                "waste_kg": round(
                    kg["waste"],
                    2,
                ),
                "waste_percentage": round(
                    kg_percentage,
                    2,
                ),

                "prepared_count": round(
                    count["prepared"],
                    2,
                ),
                "served_count": round(
                    count["served"],
                    2,
                ),
                "waste_count": round(
                    count["waste"],
                    2,
                ),
                "count_waste_percentage": round(
                    count_percentage,
                    2,
                ),
            }
        )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "total_prepared": round(
            total_prepared_kg,
            2,
        ),
        "total_served": round(
            total_served_kg,
            2,
        ),
        "total_waste": round(
            total_waste_kg,
            2,
        ),
        "waste_percentage": round(
            waste_percentage_kg,
            2,
        ),

        "total_prepared_kg": round(
            total_prepared_kg,
            2,
        ),
        "total_served_kg": round(
            total_served_kg,
            2,
        ),
        "total_waste_kg": round(
            total_waste_kg,
            2,
        ),
        "waste_percentage_kg": round(
            waste_percentage_kg,
            2,
        ),

        "total_prepared_count": round(
            total_prepared_count,
            2,
        ),
        "total_served_count": round(
            total_served_count,
            2,
        ),
        "total_waste_count": round(
            total_waste_count,
            2,
        ),
        "waste_percentage_count": round(
            waste_percentage_count,
            2,
        ),

        "item_waste": item_waste,
        "daily_trends": daily_trends,
        "weekly_trends": daily_trends,
        "monthly_trends": daily_trends,
        "meal_waste": meal_waste,
    }

# ============================================================
# REPORTS
# ============================================================


@app.post(
    "/reports/generate"
)
async def generate_report(
    report: ReportRequest,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    if report.from_date > report.to_date:
        raise HTTPException(
            status_code=400,
            detail="From date cannot be after to date.",
        )

    result = await db.execute(
        select(
            DailyConsumption
        ).where(
            DailyConsumption.date
            >= report.from_date,
            DailyConsumption.date
            <= report.to_date,
        )
        .order_by(
            DailyConsumption.date,
            DailyConsumption.id,
        )
    )

    records = result.scalars().all()

    total_prepared_kg = 0.0
    total_served_kg = 0.0
    total_waste_kg = 0.0

    total_prepared_count = 0.0
    total_served_count = 0.0
    total_waste_count = 0.0

    item_totals: dict[tuple[str, str], dict] = {}

    for record in records:
        unit = (
            record.unit.value
            if record.unit
            else "kg"
        )

        if unit == "count":
            total_prepared_count += record.prepared_kg
            total_served_count += record.served_kg
            total_waste_count += record.waste_kg
        else:
            total_prepared_kg += record.prepared_kg
            total_served_kg += record.served_kg
            total_waste_kg += record.waste_kg

        key = (
            record.item_name,
            unit,
        )

        if key not in item_totals:
            item_totals[key] = {
                "prepared": 0.0,
                "served": 0.0,
                "waste": 0.0,
            }

        item_totals[key]["prepared"] += record.prepared_kg
        item_totals[key]["served"] += record.served_kg
        item_totals[key]["waste"] += record.waste_kg

    waste_percentage_kg = (
        (total_waste_kg / total_prepared_kg) * 100
        if total_prepared_kg > 0
        else 0
    )

    waste_percentage_count = (
        (total_waste_count / total_prepared_count) * 100
        if total_prepared_count > 0
        else 0
    )

    attendance_result = await db.execute(
        select(
            func.count(MealAttendance.id)
        ).where(
            MealAttendance.date
            >= report.from_date,
            MealAttendance.date
            <= report.to_date,
            MealAttendance.status
            == AttendanceStatus.PRESENT,
        )
    )

    attended_meals = (
        attendance_result.scalar() or 0
    )

    skipped_result = await db.execute(
        select(
            func.count(MealAttendance.id)
        ).where(
            MealAttendance.date
            >= report.from_date,
            MealAttendance.date
            <= report.to_date,
            MealAttendance.status
            == AttendanceStatus.SKIPPED,
        )
    )

    skipped_meals = (
        skipped_result.scalar() or 0
    )

    item_breakdown = [
        {
            "item_name": item_name,
            "unit": unit,
            "prepared": round(
                values["prepared"],
                2,
            ),
            "served": round(
                values["served"],
                2,
            ),
            "waste": round(
                values["waste"],
                2,
            ),
        }
        for (item_name, unit), values
        in sorted(
            item_totals.items(),
            key=lambda x: x[1]["waste"],
            reverse=True,
        )
    ]

    return {
        "report": {
            "from_date": report.from_date,
            "to_date": report.to_date,
            "generated_at": datetime.now(),
        },
        "waste_summary": {
            "total_prepared_kg": round(
                total_prepared_kg,
                2,
            ),
            "total_served_kg": round(
                total_served_kg,
                2,
            ),
            "total_waste_kg": round(
                total_waste_kg,
                2,
            ),
            "waste_percentage_kg": round(
                waste_percentage_kg,
                2,
            ),
            "total_prepared_count": round(
                total_prepared_count,
                2,
            ),
            "total_served_count": round(
                total_served_count,
                2,
            ),
            "total_waste_count": round(
                total_waste_count,
                2,
            ),
            "waste_percentage_count": round(
                waste_percentage_count,
                2,
            ),
        },
        "attendance_summary": {
            "attended_meals": attended_meals,
            "skipped_meals": skipped_meals,
        },
        "item_breakdown": item_breakdown,
        "records": [
            {
                "date": record.date,
                "meal": (
                    record.meal.value
                    if record.meal
                    else None
                ),
                "item_name": record.item_name,
                "prepared": record.prepared_kg,
                "served": record.served_kg,
                "waste": record.waste_kg,
                "unit": (
                    record.unit.value
                    if record.unit
                    else "kg"
                ),
            }
            for record in records
        ],
    }

# ============================================================
# NOTIFICATIONS
# ============================================================


@app.get(
    "/notifications",
    response_model=list[NotificationResponse],
)
async def get_notifications(
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    result = await db.execute(
        select(NotificationLog)
        .order_by(
            NotificationLog.created_at.desc()
        )
        .limit(50)
    )

    return result.scalars().all()


# ============================================================
# PROFILE
# ============================================================


@app.get(
    "/profile",
    response_model=UserResponse,
)
async def profile(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
):
    return current_user


# ============================================================
# LEGACY ATTENDANCE COMPATIBILITY
# ============================================================


@app.patch(
    "/students/{student_id}/attendance",
)
async def update_legacy_attendance(
    student_id: int,
    attendance_data: AttendanceUpdate,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    result = await db.execute(
        select(Student).where(
            Student.id == student_id
        )
    )

    student = result.scalar_one_or_none()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    student.is_present_today = (
        attendance_data.is_present_today
    )

    await db.commit()
    await db.refresh(student)

    return {
        "message": "Student attendance status updated.",
        "student_id": student.id,
        "is_present_today": student.is_present_today,
    }
# ============================================================
# REPORT PDF DOWNLOAD
# ============================================================

@app.post("/reports/download")
async def download_report(
    report: ReportRequest,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    current_user: Annotated[
        User,
        Depends(require_staff),
    ],
):
    if report.from_date > report.to_date:
        raise HTTPException(
            status_code=400,
            detail="From date cannot be after to date.",
        )

    result = await db.execute(
        select(DailyConsumption)
        .where(
            DailyConsumption.date >= report.from_date,
            DailyConsumption.date <= report.to_date,
        )
        .order_by(
            DailyConsumption.date,
            DailyConsumption.id,
        )
    )

    records = result.scalars().all()

    total_prepared_kg = 0.0
    total_served_kg = 0.0
    total_waste_kg = 0.0

    total_prepared_count = 0.0
    total_served_count = 0.0
    total_waste_count = 0.0

    item_totals = {}

    for record in records:
        unit = record.unit.value if record.unit else "kg"

        if unit == "count":
            total_prepared_count += record.prepared_kg
            total_served_count += record.served_kg
            total_waste_count += record.waste_kg
        else:
            total_prepared_kg += record.prepared_kg
            total_served_kg += record.served_kg
            total_waste_kg += record.waste_kg

        key = (record.item_name, unit)

        if key not in item_totals:
            item_totals[key] = {
                "prepared": 0.0,
                "served": 0.0,
                "waste": 0.0,
            }

        item_totals[key]["prepared"] += record.prepared_kg
        item_totals[key]["served"] += record.served_kg
        item_totals[key]["waste"] += record.waste_kg

    waste_percentage_kg = (
        (total_waste_kg / total_prepared_kg) * 100
        if total_prepared_kg > 0
        else 0
    )

    waste_percentage_count = (
        (total_waste_count / total_prepared_count) * 100
        if total_prepared_count > 0
        else 0
    )

    attendance_result = await db.execute(
        select(func.count(MealAttendance.id))
        .where(
            MealAttendance.date >= report.from_date,
            MealAttendance.date <= report.to_date,
            MealAttendance.status == AttendanceStatus.PRESENT,
        )
    )

    attended_meals = attendance_result.scalar() or 0

    skipped_result = await db.execute(
        select(func.count(MealAttendance.id))
        .where(
            MealAttendance.date >= report.from_date,
            MealAttendance.date <= report.to_date,
            MealAttendance.status == AttendanceStatus.SKIPPED,
        )
    )

    skipped_meals = skipped_result.scalar() or 0

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]

    elements = []

    elements.append(
        Paragraph(
            "SMART MESS MANAGEMENT SYSTEM",
            title_style,
        )
    )

    elements.append(
        Paragraph(
            "Waste & Consumption Report",
            heading_style,
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        Paragraph(
            f"<b>From:</b> {report.from_date} &nbsp;&nbsp;&nbsp; "
            f"<b>To:</b> {report.to_date}",
            normal_style,
        )
    )

    elements.append(
        Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            normal_style,
        )
    )

    elements.append(Spacer(1, 12))

    summary_data = [
        ["Metric", "Value"],
        [
            "Total Prepared (Kg)",
            f"{total_prepared_kg:.2f} kg",
        ],
        [
            "Total Served (Kg)",
            f"{total_served_kg:.2f} kg",
        ],
        [
            "Total Waste (Kg)",
            f"{total_waste_kg:.2f} kg",
        ],
        [
            "Waste Percentage (Kg)",
            f"{waste_percentage_kg:.2f}%",
        ],
        [
            "Total Prepared (Count)",
            f"{total_prepared_count:.0f}",
        ],
        [
            "Total Served (Count)",
            f"{total_served_count:.0f}",
        ],
        [
            "Total Waste (Count)",
            f"{total_waste_count:.0f}",
        ],
        [
            "Waste Percentage (Count)",
            f"{waste_percentage_count:.2f}%",
        ],
        [
            "Attended Meals",
            str(attended_meals),
        ],
        [
            "Skipped Meals",
            str(skipped_meals),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[90 * mm, 70 * mm],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#eeeeee"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    elements.append(summary_table)

    elements.append(Spacer(1, 18))

    elements.append(
        Paragraph(
            "Item-wise Waste Breakdown",
            heading_style,
        )
    )

    elements.append(Spacer(1, 8))

    item_data = [
        [
            "Item",
            "Unit",
            "Prepared",
            "Served",
            "Waste",
        ]
    ]

    sorted_items = sorted(
        item_totals.items(),
        key=lambda x: x[1]["waste"],
        reverse=True,
    )

    for (item_name, unit), values in sorted_items:
        item_data.append(
            [
                str(item_name),
                unit,
                f"{values['prepared']:.2f}",
                f"{values['served']:.2f}",
                f"{values['waste']:.2f}",
            ]
        )

    if len(item_data) == 1:
        item_data.append(
            [
                "No records",
                "-",
                "-",
                "-",
                "-",
            ]
        )

    item_table = Table(
        item_data,
        colWidths=[
            55 * mm,
            20 * mm,
            35 * mm,
            35 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    item_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#eeeeee"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    elements.append(item_table)

    elements.append(Spacer(1, 18))

    elements.append(
        Paragraph(
            "Generated by Smart Mess Management System",
            normal_style,
        )
    )

    document.build(elements)

    buffer.seek(0)

    filename = (
        f"smart_mess_report_"
        f"{report.from_date}_"
        f"{report.to_date}.pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )

