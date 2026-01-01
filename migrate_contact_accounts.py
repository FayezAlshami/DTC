"""Migration script to create contact_accounts table."""
import asyncio
from database.base import AsyncSessionLocal, engine, Base
from database.models import ContactAccount
from sqlalchemy import text


async def create_contact_accounts_table():
    """Create contact_accounts table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'contact_accounts'
            );
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            print("📋 إنشاء جدول حسابات التواصل...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ تم إنشاء جدول حسابات التواصل")
        else:
            print("✅ جدول حسابات التواصل موجود بالفعل")


async def main():
    """Run migration."""
    print("🚀 بدء migration لحسابات التواصل...\n")
    
    try:
        await create_contact_accounts_table()
        print("\n✅ تم إكمال migration بنجاح!")
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء migration: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

