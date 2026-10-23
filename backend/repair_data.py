from __future__ import annotations

import asyncio
import secrets
from collections import defaultdict

from sqlalchemy import select
from database import AsyncSessionLocal
from models import Student, Menu, MenuItem, DailyConsumption


DEPARTMENTS = ["CSE", "IT", "ECE", "EEE", "MECH"]
YEARS = ["I", "II", "III", "IV"]
BLOCKS = ["A", "B", "C", "D"]


async def repair_students(session):
    result = await session.execute(select(Student).order_by(Student.id))
    students = result.scalars().all()

    repaired = 0

    for index, student in enumerate(students, start=1):

        changed = False

        if not student.student_code:
            student.student_code = f"SM{student.id:04d}"
            changed = True

        if not student.department:
            student.department = DEPARTMENTS[(index - 1) % len(DEPARTMENTS)]
            changed = True

        if not student.year:
            student.year = YEARS[(index - 1) % len(YEARS)]
            changed = True

        if not student.block:
            student.block = BLOCKS[(index - 1) % len(BLOCKS)]
            changed = True

        if not student.room_number:
            room_number = 100 + ((index - 1) % 100) + 1
            student.room_number = str(room_number)
            changed = True

        if not student.qr_token:
            student.qr_token = f"SMQR-{student.student_code}-{secrets.token_hex(4)}"
            changed = True

        if changed:
            repaired += 1

    await session.commit()

    print(f"Students checked: {len(students)}")
    print(f"Students repaired: {repaired}")


async def repair_consumption(session):
    menu_result = await session.execute(
        select(MenuItem, Menu)
        .join(Menu, MenuItem.menu_id == Menu.id)
    )

    menu_items = menu_result.all()

    # Exact lookup:
    # (date, item_name) -> meal/menu_item_id
    item_lookup = {}

    for menu_item, menu in menu_items:
        key = (menu.date, menu_item.item_name.strip().lower())

        # Keep the first exact match if duplicate item names exist.
        if key not in item_lookup:
            item_lookup[key] = (
                menu_item.meal,
                menu_item.id,
            )

    result = await session.execute(
        select(DailyConsumption).order_by(
            DailyConsumption.date,
            DailyConsumption.id
        )
    )

    records = result.scalars().all()

    repaired = 0
    still_missing = 0

    for record in records:

        if record.meal is not None and record.menu_item_id is not None:
            continue

        key = (
            record.date,
            record.item_name.strip().lower()
        )

        match = item_lookup.get(key)

        if match:
            meal, menu_item_id = match

            if record.meal is None:
                record.meal = meal

            if record.menu_item_id is None:
                record.menu_item_id = menu_item_id

            repaired += 1

        else:
            still_missing += 1

    await session.commit()

    print(f"Consumption records checked: {len(records)}")
    print(f"Consumption records repaired: {repaired}")
    print(f"Consumption records still without meal mapping: {still_missing}")


async def show_summary(session):
    student_result = await session.execute(select(Student))
    students = student_result.scalars().all()

    consumption_result = await session.execute(
        select(DailyConsumption)
    )
    consumption = consumption_result.scalars().all()

    missing_student_code = sum(
        1 for s in students if not s.student_code
    )

    missing_department = sum(
        1 for s in students if not s.department
    )

    missing_year = sum(
        1 for s in students if not s.year
    )

    missing_block = sum(
        1 for s in students if not s.block
    )

    missing_room = sum(
        1 for s in students if not s.room_number
    )

    missing_qr = sum(
        1 for s in students if not s.qr_token
    )

    missing_meal = sum(
        1 for c in consumption if c.meal is None
    )

    total_prepared = sum(c.prepared_kg for c in consumption)
    total_served = sum(c.served_kg for c in consumption)
    total_waste = sum(c.waste_kg for c in consumption)

    print()
    print("=" * 60)
    print("REPAIR VERIFICATION")
    print("=" * 60)

    print()
    print("STUDENT DATA")
    print(f"Total students       : {len(students)}")
    print(f"Missing student code : {missing_student_code}")
    print(f"Missing department   : {missing_department}")
    print(f"Missing year         : {missing_year}")
    print(f"Missing block        : {missing_block}")
    print(f"Missing room         : {missing_room}")
    print(f"Missing QR           : {missing_qr}")

    print()
    print("CONSUMPTION DATA")
    print(f"Consumption records  : {len(consumption)}")
    print(f"Missing meal         : {missing_meal}")

    print()
    print("WASTE TOTALS")
    print(f"Prepared             : {total_prepared:.2f} kg")
    print(f"Served               : {total_served:.2f} kg")
    print(f"Waste                : {total_waste:.2f} kg")

    if total_prepared > 0:
        waste_percentage = (total_waste / total_prepared) * 100
    else:
        waste_percentage = 0

    print(f"Waste percentage     : {waste_percentage:.2f}%")

    print("=" * 60)


async def main():
    print()
    print("=" * 60)
    print("SMART MESS DATA REPAIR")
    print("=" * 60)

    async with AsyncSessionLocal() as session:

        print()
        print("Step 1: Repairing student details...")
        await repair_students(session)

        print()
        print("Step 2: Repairing consumption meal information...")
        await repair_consumption(session)

        print()
        print("Step 3: Verifying database...")
        await show_summary(session)

    print()
    print("DATA REPAIR COMPLETED.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
