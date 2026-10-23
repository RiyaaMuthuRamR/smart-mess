
from datetime import date, timedelta

from passlib.context import CryptContext
from sqlalchemy import select

from database import AsyncSessionLocal, init_database
from models import DailyConsumption, Menu, Student, User, UserRole


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


TEST_PHONE_NUMBERS = [
    "8807942420",
    "7558195795",
    "9952654324",
]


async def seed_users(session) -> None:
    result = await session.execute(select(User))
    existing_user = result.scalars().first()

    if existing_user is not None:
        return

    users = [
        User(
            username="warden",
            hashed_password=pwd_context.hash("Warden@123"),
            role=UserRole.WARDEN,
        ),
        User(
            username="operator",
            hashed_password=pwd_context.hash("Operator@123"),
            role=UserRole.OPERATOR,
        ),
    ]

    session.add_all(users)


async def seed_students(session) -> None:
    result = await session.execute(select(Student))
    existing_student = result.scalars().first()

    if existing_student is not None:
        return

    students = [
        Student(
            name="Riya",
            roll_number="24CS001",
            phone_number=TEST_PHONE_NUMBERS[0],
            is_present_today=True,
        ),
        Student(
            name="Arunima",
            roll_number="24CS002",
            phone_number=TEST_PHONE_NUMBERS[1],
            is_present_today=True,
        ),
        Student(
            name="Priyadharshini",
            roll_number="24CS003",
            phone_number=TEST_PHONE_NUMBERS[2],
            is_present_today=True,
        ),
        Student(
            name="Keerthana",
            roll_number="24CS004",
            phone_number="9876543210",
            is_present_today=True,
        ),
        Student(
            name="Harini",
            roll_number="24CS005",
            phone_number="9876543211",
            is_present_today=True,
        ),
        Student(
            name="Nandhini",
            roll_number="24CS006",
            phone_number="9876543212",
            is_present_today=False,
        ),
        Student(
            name="Sanjana",
            roll_number="24CS007",
            phone_number="9876543213",
            is_present_today=True,
        ),
        Student(
            name="Deepika",
            roll_number="24CS008",
            phone_number="9876543214",
            is_present_today=True,
        ),
        Student(
            name="Swetha",
            roll_number="24CS009",
            phone_number="9876543215",
            is_present_today=False,
        ),
        Student(
            name="Kavya",
            roll_number="24CS010",
            phone_number="9876543216",
            is_present_today=True,
        ),
        Student(
            name="Dhivya",
            roll_number="24CS011",
            phone_number="9876543217",
            is_present_today=True,
        ),
        Student(
            name="Pavithra",
            roll_number="24CS012",
            phone_number="9876543218",
            is_present_today=True,
        ),
    ]

    session.add_all(students)


async def seed_menus(session) -> None:
    result = await session.execute(select(Menu))
    existing_menu = result.scalars().first()

    if existing_menu is not None:
        return

    today = date.today()

    menus = [
        Menu(
            date=today - timedelta(days=6),
            breakfast="Idli, Sambar, Coconut Chutney",
            lunch="Rice, Sambar, Beans Poriyal, Curd",
            dinner="Chapati, Vegetable Kurma",
        ),
        Menu(
            date=today - timedelta(days=5),
            breakfast="Pongal, Vada, Chutney",
            lunch="Tomato Rice, Potato Fry, Curd",
            dinner="Dosa, Sambar, Chutney",
        ),
        Menu(
            date=today - timedelta(days=4),
            breakfast="Poori, Potato Masala",
            lunch="Rice, Rasam, Cabbage Poriyal, Curd",
            dinner="Chapati, Dal",
        ),
        Menu(
            date=today - timedelta(days=3),
            breakfast="Idli, Sambar, Chutney",
            lunch="Lemon Rice, Vegetable Kurma, Curd",
            dinner="Parotta, Vegetable Salna",
        ),
        Menu(
            date=today - timedelta(days=2),
            breakfast="Dosa, Sambar, Chutney",
            lunch="Rice, Kara Kuzhambu, Beans Poriyal, Curd",
            dinner="Chapati, Chana Masala",
        ),
        Menu(
            date=today - timedelta(days=1),
            breakfast="Pongal, Sambar, Chutney",
            lunch="Jeera Rice, Dal, Carrot Poriyal, Curd",
            dinner="Dosa, Sambar, Chutney",
        ),
        Menu(
            date=today,
            breakfast="Idli, Sambar, Chutney",
            lunch="Rice, Sambar, Potato Fry, Curd",
            dinner="Chapati, Vegetable Kurma",
        ),
    ]

    session.add_all(menus)


async def seed_consumption(session) -> None:
    result = await session.execute(
        select(DailyConsumption).limit(1)
    )

    existing_consumption = result.scalars().first()

    if existing_consumption is not None:
        return

    today = date.today()

    records_by_day = {
        6: [
            ("Idli", 18.0, 15.5),
            ("Sambar", 12.0, 10.8),
            ("Rice", 28.0, 25.2),
            ("Beans Poriyal", 8.0, 6.9),
            ("Chapati", 14.0, 12.5),
        ],
        5: [
            ("Pongal", 20.0, 17.8),
            ("Vada", 7.0, 5.9),
            ("Tomato Rice", 30.0, 27.5),
            ("Potato Fry", 9.0, 7.8),
            ("Dosa", 16.0, 14.4),
        ],
        4: [
            ("Poori", 15.0, 13.2),
            ("Potato Masala", 10.0, 8.9),
            ("Rice", 29.0, 26.7),
            ("Cabbage Poriyal", 8.0, 7.0),
            ("Chapati", 15.0, 13.6),
        ],
        3: [
            ("Idli", 19.0, 17.1),
            ("Lemon Rice", 27.0, 24.0),
            ("Vegetable Kurma", 10.0, 8.4),
            ("Parotta", 18.0, 15.7),
            ("Vegetable Salna", 12.0, 10.3),
        ],
        2: [
            ("Dosa", 18.0, 16.0),
            ("Rice", 31.0, 27.4),
            ("Kara Kuzhambu", 11.0, 9.2),
            ("Beans Poriyal", 8.0, 6.8),
            ("Chapati", 16.0, 14.2),
        ],
        1: [
            ("Pongal", 21.0, 18.6),
            ("Jeera Rice", 28.0, 24.9),
            ("Dal", 12.0, 10.5),
            ("Carrot Poriyal", 8.0, 6.7),
            ("Dosa", 17.0, 15.1),
        ],
        0: [
            ("Idli", 20.0, 17.6),
            ("Sambar", 13.0, 11.1),
            ("Rice", 32.0, 27.8),
            ("Potato Fry", 10.0, 8.1),
            ("Chapati", 17.0, 14.6),
        ],
    }

    records = []

    for days_ago, items in records_by_day.items():
        record_date = today - timedelta(days=days_ago)

        for item_name, prepared, served in items:
            waste = round(prepared - served, 2)

            records.append(
                DailyConsumption(
                    date=record_date,
                    item_name=item_name,
                    prepared_kg=prepared,
                    served_kg=served,
                    waste_kg=waste,
                )
            )

    session.add_all(records)


async def seed_database() -> None:
    print("Initializing database...")

    await init_database()

    async with AsyncSessionLocal() as session:
        await seed_users(session)
        await seed_students(session)
        await seed_menus(session)

        await session.flush()

        await seed_consumption(session)

        await session.commit()

    print()
    print("==============================================")
    print("Smart Mess database seeded successfully.")
    print("==============================================")
    print()
    print("Demo login accounts:")
    print("Warden:")
    print("  Username: warden")
    print("  Password: Warden@123")
    print()
    print("Operator:")
    print("  Username: operator")
    print("  Password: Operator@123")
    print()
    print("WhatsApp test students:")
    print("  Riya            -> +91 8807942420")
    print("  Arunima         -> +91 7558195795")
    print("  Priyadharshini  -> +91 9952654324")
    print()
    print("Synthetic students: 9")
    print("Historical menus: 7")
    print("Historical consumption: 35")
    print()
    print("Database file: smartmess.db")
    print("==============================================")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_database())
