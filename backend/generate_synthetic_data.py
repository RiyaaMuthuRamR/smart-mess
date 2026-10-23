from __future__ import annotations

import asyncio
import random
import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, select

from database import AsyncSessionLocal, init_database
from models import (
    AttendanceStatus,
    DailyConsumption,
    MealAttendance,
    MealType,
    Menu,
    MenuItem,
    Student,
)


random.seed(20261007)


START_DATE = date(2026, 8, 8)
END_DATE = date(2026, 9, 6)

TOTAL_STUDENTS = 200


FIRST_NAMES = [
    "Aarav",
    "Aditya",
    "Akash",
    "Akshaya",
    "Ananya",
    "Anjali",
    "Arjun",
    "Ashwin",
    "Bhavya",
    "Deepika",
    "Dhanya",
    "Divya",
    "Harini",
    "Ishita",
    "Janani",
    "Karthik",
    "Keerthana",
    "Kavin",
    "Kavya",
    "Lakshmi",
    "Madhumitha",
    "Manoj",
    "Meena",
    "Monisha",
    "Nandhini",
    "Navin",
    "Naveen",
    "Nikhil",
    "Pavithra",
    "Pranav",
    "Praveen",
    "Priya",
    "Priyadharshini",
    "Rahul",
    "Rakesh",
    "Riya",
    "Sanjana",
    "Saranya",
    "Shreya",
    "Sowmya",
    "Swetha",
    "Tamilselvi",
    "Varsha",
    "Vignesh",
    "Vishnu",
]


LAST_NAMES = [
    "Kumar",
    "Raj",
    "Raman",
    "Krishnan",
    "Muthu",
    "Sharma",
    "Iyer",
    "Reddy",
    "Nair",
    "Das",
    "Menon",
    "Prakash",
    "Singh",
    "Devi",
    "Balan",
]


DEPARTMENTS = [
    "CSE",
    "IT",
    "ECE",
    "EEE",
    "MECH",
]


YEARS = [
    "1st Year",
    "2nd Year",
    "3rd Year",
    "4th Year",
]


BLOCKS = [
    "A Block",
    "B Block",
    "C Block",
    "D Block",
]


MENU_ITEMS = {
    MealType.BREAKFAST: [
        ("Idli", 500),
        ("Sambar", 500),
        ("Chutney", 500),
    ],
    MealType.LUNCH: [
        ("Rice", 500),
        ("Sambar", 500),
        ("Poriyal", 500),
        ("Curd", 500),
    ],
    MealType.DINNER: [
        ("Chapati", 500),
        ("Kurma", 500),
        ("Rice", 500),
        ("Dal", 500),
    ],
}


MEAL_TIMES = {
    MealType.BREAKFAST: (
        time(7, 15),
        time(9, 0),
    ),
    MealType.LUNCH: (
        time(12, 15),
        time(14, 15),
    ),
    MealType.DINNER: (
        time(19, 0),
        time(21, 0),
    ),
}


def daterange(start: date, end: date):
    current = start

    while current <= end:
        yield current
        current += timedelta(days=1)


def generate_phone(index: int) -> str:
    return f"90000{index:05d}"


def generate_student(index: int) -> Student:
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    name = f"{first_name} {last_name}"

    student_code = f"SM{1000 + index}"

    roll_number = f"23{random.choice(['CS', 'IT', 'EC', 'EE', 'ME'])}{index:03d}"

    block = random.choice(BLOCKS)

    room_number = f"{random.randint(1, 4)}{random.randint(0, 9):02d}"

    qr_token = f"SMQR-{uuid.uuid4().hex[:20]}"

    return Student(
        name=name,
        roll_number=roll_number,
        phone_number=generate_phone(index),
        is_present_today=True,
        student_code=student_code,
        department=random.choice(DEPARTMENTS),
        year=random.choice(YEARS),
        block=block,
        room_number=room_number,
        qr_token=qr_token,
    )


def create_menu_items(menu: Menu) -> list[MenuItem]:
    items = []

    for meal, meal_items in MENU_ITEMS.items():
        for item_name, base_servings in meal_items:

            variation = random.randint(-30, 30)

            item = MenuItem(
                menu=menu,
                meal=meal,
                item_name=item_name,
                planned_servings=base_servings + variation,
            )

            items.append(item)

    return items


def generate_attendance(
    student: Student,
    current_date: date,
    meal: MealType,
) -> MealAttendance | None:

    probabilities = {
        MealType.BREAKFAST: 0.88,
        MealType.LUNCH: 0.84,
        MealType.DINNER: 0.90,
    }

    present_probability = probabilities[meal]

    if random.random() <= present_probability:

        start_time, end_time = MEAL_TIMES[meal]

        start_seconds = (
            start_time.hour * 3600
            + start_time.minute * 60
        )

        end_seconds = (
            end_time.hour * 3600
            + end_time.minute * 60
        )

        random_seconds = random.randint(
            start_seconds,
            end_seconds,
        )

        hour = random_seconds // 3600
        minute = (random_seconds % 3600) // 60
        second = random_seconds % 60

        scan_datetime = datetime.combine(
            current_date,
            time(hour, minute, second),
        )

        return MealAttendance(
            student_id=student.id,
            date=current_date,
            meal=meal,
            status=AttendanceStatus.PRESENT,
            scan_time=scan_datetime,
        )

    return MealAttendance(
        student_id=student.id,
        date=current_date,
        meal=meal,
        status=AttendanceStatus.SKIPPED,
        scan_time=None,
    )


def generate_consumption(
    current_date: date,
    menu: Menu,
    menu_item: MenuItem,
    attendance_count: int,
):
    planned = menu_item.planned_servings

    attendance_factor = max(
        0.55,
        min(
            1.0,
            attendance_count / TOTAL_STUDENTS,
        ),
    )

    base_prepared = planned * random.uniform(
        0.075,
        0.105,
    )

    prepared = base_prepared * random.uniform(
        0.95,
        1.08,
    )

    expected_served_ratio = min(
        0.96,
        attendance_factor * random.uniform(
            0.86,
            1.00,
        ),
    )

    served = prepared * expected_served_ratio

    if served > prepared:
        served = prepared

    waste = prepared - served

    return DailyConsumption(
        date=current_date,
        item_name=menu_item.item_name,
        prepared_kg=round(prepared, 2),
        served_kg=round(served, 2),
        waste_kg=round(waste, 2),
        meal=menu_item.meal,
        menu_item_id=menu_item.id,
    )


async def clear_previous_synthetic_data(session):
    print("Removing previous synthetic dataset if present...")

    synthetic_dates = list(
        daterange(
            START_DATE,
            END_DATE,
        )
    )

    await session.execute(
        delete(MealAttendance).where(
            MealAttendance.date.in_(synthetic_dates)
        )
    )

    await session.execute(
        delete(DailyConsumption).where(
            DailyConsumption.date.in_(synthetic_dates)
        )
    )

    old_menus_result = await session.execute(
        select(Menu).where(
            Menu.date.in_(synthetic_dates)
        )
    )

    old_menus = old_menus_result.scalars().all()

    for menu in old_menus:
        await session.delete(menu)

    await session.commit()


async def create_students(session):
    result = await session.execute(
        select(Student)
    )

    existing_students = result.scalars().all()

    existing_codes = {
        student.student_code
        for student in existing_students
        if student.student_code
    }

    created = 0

    for index in range(1, TOTAL_STUDENTS + 1):

        student_code = f"SM{1000 + index}"

        if student_code in existing_codes:
            continue

        student = generate_student(index)

        session.add(student)

        created += 1

    await session.commit()

    print(
        f"Students created: {created}"
    )


async def load_students(session):
    result = await session.execute(
        select(Student)
        .order_by(Student.id)
    )

    return result.scalars().all()


async def create_history(session, students):
    total_attendance = 0
    total_consumption = 0
    total_menus = 0

    for current_date in daterange(
        START_DATE,
        END_DATE,
    ):

        menu = Menu(
            date=current_date,
            breakfast="Idli, Sambar, Chutney",
            lunch="Rice, Sambar, Poriyal, Curd",
            dinner="Chapati, Kurma, Rice, Dal",
        )

        session.add(menu)

        await session.flush()

        menu_items = create_menu_items(menu)

        for item in menu_items:
            session.add(item)

        await session.flush()

        total_menus += 1

        for meal in MealType:

            attendance_count = 0

            for student in students:

                attendance = generate_attendance(
                    student,
                    current_date,
                    meal,
                )

                session.add(attendance)

                if attendance.status == AttendanceStatus.PRESENT:
                    attendance_count += 1
                    total_attendance += 1

            meal_items = [
                item
                for item in menu_items
                if item.meal == meal
            ]

            for item in meal_items:

                consumption = generate_consumption(
                    current_date,
                    menu,
                    item,
                    attendance_count,
                )

                session.add(consumption)

                total_consumption += 1

        if current_date.day % 5 == 0:
            await session.commit()

        print(
            f"Generated: {current_date}"
        )

    await session.commit()

    return (
        total_menus,
        total_attendance,
        total_consumption,
    )


async def main():
    print("=" * 60)
    print("SMART MESS SYNTHETIC DATA GENERATOR")
    print("=" * 60)

    print(
        f"Date range: {START_DATE} to {END_DATE}"
    )

    print(
        f"Students: {TOTAL_STUDENTS}"
    )

    print()

    await init_database()

    async with AsyncSessionLocal() as session:

        await clear_previous_synthetic_data(
            session
        )

        await create_students(
            session
        )

        students = await load_students(
            session
        )

        print(
            f"Total students currently in database: "
            f"{len(students)}"
        )

        if len(students) < TOTAL_STUDENTS:
            raise RuntimeError(
                "Not enough students available."
            )

        print()
        print(
            "Generating 30 days of meal history..."
        )

        (
            total_menus,
            total_attendance,
            total_consumption,
        ) = await create_history(
            session,
            students[:TOTAL_STUDENTS],
        )

        print()
        print("=" * 60)
        print("SYNTHETIC DATA GENERATION COMPLETE")
        print("=" * 60)

        print(
            f"Students available: {len(students)}"
        )

        print(
            f"Historical days: 30"
        )

        print(
            f"Menus created: {total_menus}"
        )

        print(
            f"Attendance records: {total_attendance}"
        )

        print(
            f"Consumption records: {total_consumption}"
        )

        print(
            "Date range: "
            f"{START_DATE} → {END_DATE}"
        )

        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
