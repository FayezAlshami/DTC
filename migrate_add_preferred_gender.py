"""Migration script to add preferred_gender column to service_requests table."""
import asyncio
from database.base import engine
from sqlalchemy import text


async def add_preferred_gender_column():
    """Add preferred_gender column to service_requests table."""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'service_requests'
                AND column_name = 'preferred_gender'
            );
        """))
        column_exists = result.scalar()
        
        if not column_exists:
            print("📋 إضافة عمود preferred_gender إلى جدول service_requests...")
            
            # Check if gender enum exists, if not create it
            enum_exists = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'gender'
                );
            """))
            
            if not enum_exists.scalar():
                await conn.execute(text("""
                    CREATE TYPE gender AS ENUM ('male', 'female', 'other');
                """))
                print("✅ تم إنشاء enum gender")
            
            # Add column with nullable initially
            await conn.execute(text("""
                ALTER TABLE service_requests 
                ADD COLUMN preferred_gender gender;
            """))
            
            print("✅ تم إضافة عمود preferred_gender")
        else:
            print("✅ عمود preferred_gender موجود بالفعل")


async def main():
    """Run migration."""
    print("🚀 بدء migration لإضافة preferred_gender...\n")
    
    try:
        await add_preferred_gender_column()
        print("\n✅ تم إكمال migration بنجاح!")
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء migration: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

