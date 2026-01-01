"""Migration script to update telegram_id column to BIGINT."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def migrate_telegram_id():
    """Migrate telegram_id column from INTEGER to BIGINT."""
    print("🔄 بدء تحديث عمود telegram_id إلى BIGINT...")
    
    async with engine.begin() as conn:
        try:
            # Check if column is already BIGINT
            result = await conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'telegram_id'
            """))
            
            row = result.fetchone()
            if row and row[0] == 'bigint':
                print("✅ العمود telegram_id هو بالفعل BIGINT. لا حاجة للتحديث.")
                return
            
            # Update column type to BIGINT
            print("📝 تحديث نوع العمود...")
            await conn.execute(text("ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT"))
            print("✅ تم تحديث عمود telegram_id بنجاح!")
            
        except Exception as e:
            print(f"❌ خطأ أثناء التحديث: {e}")
            print("\nيمكنك تشغيل هذا الأمر يدوياً في PostgreSQL:")
            print("ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT;")


if __name__ == "__main__":
    asyncio.run(migrate_telegram_id())

