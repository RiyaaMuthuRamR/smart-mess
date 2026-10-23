import asyncio

from sqlalchemy import text

from database import engine


async def column_exists(connection, table_name: str, column_name: str) -> bool:
    result = await connection.execute(
        text(f"PRAGMA table_info({table_name})")
    )

    columns = result.fetchall()

    return any(row[1] == column_name for row in columns)


async def add_column_if_missing(
    connection,
    table_name: str,
    column_definition: str,
):
    column_name = column_definition.split()[0]

    if not await column_exists(
        connection,
        table_name,
        column_name,
    ):
        await connection.execute(
            text(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_definition}"
            )
        )
        print(
            f"Added column: {table_name}.{column_name}"
        )
    else:
        print(
            f"Already exists: {table_name}.{column_name}"
        )


async def migrate():
    print("Starting Smart Mess database migration...")

    async with engine.begin() as connection:

        # Student fields
        await add_column_if_missing(
            connection,
            "students",
            "student_code VARCHAR(50)",
        )

        await add_column_if_missing(
            connection,
            "students",
            "department VARCHAR(100)",
        )

        await add_column_if_missing(
            connection,
            "students",
            "year VARCHAR(30)",
        )

        await add_column_if_missing(
            connection,
            "students",
            "block VARCHAR(50)",
        )

        await add_column_if_missing(
            connection,
            "students",
            "room_number VARCHAR(30)",
        )

        await add_column_if_missing(
            connection,
            "students",
            "qr_token VARCHAR(150)",
        )

        # Consumption fields
        await add_column_if_missing(
            connection,
            "daily_consumption",
            "meal VARCHAR(20)",
        )

        await add_column_if_missing(
            connection,
            "daily_consumption",
            "menu_item_id INTEGER",
        )

        print("Creating new tables...")

        await connection.run_sync(
            __import__("database").Base.metadata.create_all
        )

    print("Database migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(migrate())
