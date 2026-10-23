from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models import AttendanceStatus, MealType, UnitType, UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    roll_number: str = Field(min_length=1, max_length=50)
    phone_number: str = Field(min_length=10, max_length=20)

    student_code: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    department: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    year: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    block: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    room_number: Optional[str] = Field(
        default=None,
        max_length=30,
    )


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    roll_number: str
    phone_number: str
    is_present_today: bool

    student_code: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    block: Optional[str] = None
    room_number: Optional[str] = None
    qr_token: Optional[str] = None


class AttendanceUpdate(BaseModel):
    is_present_today: bool


class AttendanceScan(BaseModel):
    student_identifier: str = Field(
        min_length=1,
        max_length=150,
    )

    meal: MealType


class AttendanceResponse(BaseModel):
    id: int
    student_id: int
    date: date
    meal: MealType
    status: AttendanceStatus
    scan_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MenuItemCreate(BaseModel):
    item_name: str = Field(
        min_length=1,
        max_length=150,
    )

    planned_servings: int = Field(
        gt=0,
        le=100000,
    )

    unit: UnitType = UnitType.KG


class MealMenuCreate(BaseModel):
    meal: MealType
    items: list[MenuItemCreate] = Field(
        min_length=1,
    )


class MenuCreate(BaseModel):
    date: date
    meals: list[MealMenuCreate] = Field(
        min_length=3,
        max_length=3,
    )

    @model_validator(mode="after")
    def validate_meals(self):
        meal_names = [meal.meal for meal in self.meals]

        if len(set(meal_names)) != 3:
            raise ValueError(
                "A menu must contain exactly one Breakfast, one Lunch, and one Dinner section."
            )

        required_meals = {
            MealType.BREAKFAST,
            MealType.LUNCH,
            MealType.DINNER,
        }

        if set(meal_names) != required_meals:
            raise ValueError(
                "A menu must contain exactly one Breakfast, one Lunch, and one Dinner section."
            )

        return self


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal: MealType
    item_name: str
    planned_servings: int
    unit: UnitType


class MenuResponse(BaseModel):
    id: int
    date: date
    items: list[MenuItemResponse]


class ConsumptionCreate(BaseModel):
    date: date

    meal: MealType

    item_name: str = Field(
        min_length=1,
        max_length=150,
    )

    prepared_kg: float = Field(
        gt=0,
        le=100000,
    )

    served_kg: float = Field(
        ge=0,
        le=100000,
    )


class ConsumptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    meal: Optional[MealType] = None
    item_name: str
    prepared_kg: float
    served_kg: float
    waste_kg: float
    unit: UnitType
    menu_item_id: Optional[int] = None


class StudentMealHistory(BaseModel):
    date: date
    meal: MealType
    time: Optional[datetime] = None
    status: AttendanceStatus


class StudentHistoryResponse(BaseModel):
    student: StudentResponse

    total_meals: int
    attended: int
    skipped: int

    history: list[StudentMealHistory]


class DashboardMealSummary(BaseModel):
    meal: MealType
    attended: int
    not_yet_attended: int
    skipped: int
    total_students: int


class DashboardResponse(BaseModel):
    today: date
    user: UserResponse

    menu: Optional[MenuResponse] = None

    attendance: list[DashboardMealSummary]

    total_students: int

    present_students: int = 0
    absent_students: int = 0
    menu_count: int = 0
    consumption_count: int = 0

    total_prepared_kg: float = 0
    total_served_kg: float = 0
    total_waste_kg: float = 0
    today_waste_percentage: float = 0

    total_prepared_count: float = 0
    total_served_count: float = 0
    total_waste_count: float = 0
    today_count_waste_percentage: float = 0

    today_menu: Optional[MenuResponse] = None


class WasteRecord(BaseModel):
    date: date
    meal: Optional[MealType] = None
    item_name: str
    prepared_kg: float
    served_kg: float
    waste_kg: float
    unit: UnitType = UnitType.KG


class AnalyticsResponse(BaseModel):
    total_prepared_kg: float
    total_served_kg: float
    total_waste_kg: float
    waste_percentage: float

    weekly_trends: list[dict]
    monthly_trends: list[dict]
    item_waste: list[dict]


class ReportRequest(BaseModel):
    from_date: date
    to_date: date


class MessageResponse(BaseModel):
    message: str


class NotificationResponse(BaseModel):
    notification_type: str
    title: str
    message: str
    recipient_count: int
    status: str
    created_at: datetime