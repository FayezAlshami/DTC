"""Migration script to add specializations table and initial data."""
import asyncio
from database.base import AsyncSessionLocal, engine, Base
from database.models import Specialization
from sqlalchemy import text


async def create_specializations_table():
    """Create specializations table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'specializations'
            );
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            print("📋 إنشاء جدول الاختصاصات...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ تم إنشاء جدول الاختصاصات")
        else:
            print("✅ جدول الاختصاصات موجود بالفعل")


async def add_initial_specializations():
    """Add initial specializations."""
    async with AsyncSessionLocal() as session:
        # Initial specializations
        initial_specializations = [
            {"name": "إلكترون", "display_order": 1},
            {"name": "معلوماتية", "display_order": 2},
            {"name": "ذكاء", "display_order": 3},
            {"name": "اتصالات", "display_order": 4},
        ]
        
        print("\n📋 إضافة الاختصاصات الأولية...")
        added_count = 0
        
        for spec_data in initial_specializations:
            # Check if specialization already exists
            from sqlalchemy import select
            result = await session.execute(
                select(Specialization).where(Specialization.name == spec_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                specialization = Specialization(
                    name=spec_data["name"],
                    display_order=spec_data["display_order"],
                    is_active=True
                )
                session.add(specialization)
                added_count += 1
                print(f"  ✅ تم إضافة: {spec_data['name']}")
            else:
                print(f"  ℹ️  موجود بالفعل: {spec_data['name']}")
        
        await session.commit()
        print(f"\n✅ تم إضافة {added_count} اختصاص جديد")


async def main():
    """Run migration."""
    print("🚀 بدء migration للاختصاصات...\n")
    
    try:
        await create_specializations_table()
        await add_initial_specializations()
        print("\n✅ تم إكمال migration بنجاح!")
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء migration: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

