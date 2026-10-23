from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserRole(str, Enum):
    WARDEN = "warden"
    OPERATOR = "operator"


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class UnitType(str, Enum):
    KG = "kg"
    COUNT = "count"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    SKIPPED = "skipped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="userrole"),
        nullable=False,
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    roll_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    notification_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    is_present_today: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # New student information
    student_code: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    year: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    block: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    room_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    qr_token: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        nullable=True,
        index=True,
    )

    attendance_records: Mapped[list["MealAttendance"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        unique=True,
        nullable=False,
        index=True,
    )

    # Existing fields retained for compatibility
    breakfast: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    lunch: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    dinner: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    items: Mapped[list["MenuItem"]] = relationship(
        back_populates="menu",
        cascade="all, delete-orphan",
    )

    consumption_records: Mapped[list["DailyConsumption"]] = relationship(
        back_populates="menu",
        cascade="all, delete-orphan",
    )


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    menu_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("menus.id"),
        nullable=False,
        index=True,
    )

    meal: Mapped[MealType] = mapped_column(
        SQLEnum(MealType, name="mealtype"),
        nullable=False,
        index=True,
    )

    item_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    planned_servings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    unit: Mapped[UnitType] = mapped_column(
        SQLEnum(UnitType, name="unittype", values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
        default=UnitType.KG,
    )

    menu: Mapped["Menu"] = relationship(
        back_populates="items",
    )

    consumption_records: Mapped[list["DailyConsumption"]] = relationship(
        back_populates="menu_item",
    )


class MealAttendance(Base):
    __tablename__ = "meal_attendance"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    meal: Mapped[MealType] = mapped_column(
        SQLEnum(MealType, name="mealtype"),
        nullable=False,
        index=True,
    )

    status: Mapped[AttendanceStatus] = mapped_column(
        SQLEnum(
            AttendanceStatus,
            name="attendancestatus",
        ),
        nullable=False,
    )

    scan_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    student: Mapped["Student"] = relationship(
        back_populates="attendance_records",
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "date",
            "meal",
            name="uq_student_meal_date",
        ),
    )


class DailyConsumption(Base):
    __tablename__ = "daily_consumption"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        ForeignKey("menus.date"),
        nullable=False,
        index=True,
    )

    item_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    prepared_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    served_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    waste_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    unit: Mapped[UnitType] = mapped_column(
        SQLEnum(UnitType, name="unittype", values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
        default=UnitType.KG,
    )

    # New fields
    meal: Mapped[MealType | None] = mapped_column(
        SQLEnum(MealType, name="mealtype"),
        nullable=True,
        index=True,
    )

    menu_item_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("menu_items.id"),
        nullable=True,
        index=True,
    )

    menu: Mapped["Menu"] = relationship(
        back_populates="consumption_records",
    )

    menu_item: Mapped["MenuItem | None"] = relationship(
        back_populates="consumption_records",
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    recipient_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="simulated",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


class DatabaseTimestampMixin:
    created_at: Mapped[datetime]