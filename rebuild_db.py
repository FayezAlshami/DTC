import asyncio
from database.base import Base
from database.session import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def rebuild_database():
    print("=== Rebuilding Database ===")

    async with engine.begin() as conn:
        print("Dropping all tables…")
        await conn.run_sync(Base.metadata.drop_all)

        print("Dropping old ENUM types…")
        enum_types = [
            "servicestatus", 
            "requeststatus", 
            "contactrequeststatus",
            "userrole",
            "gender"
        ]

        for enum_name in enum_types:
            await conn.execute(
                text(f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                        DROP TYPE {enum_name} CASCADE;
                    END IF;
                END$$;
                """)
            )

        print("Creating tables + ENUMs fresh…")
        await conn.run_sync(Base.metadata.create_all)

    print("=== DONE ===")


if __name__ == "__main__":
    asyncio.run(rebuild_database())
