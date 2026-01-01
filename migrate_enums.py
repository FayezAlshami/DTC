"""Migration script to update enum types in PostgreSQL."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def migrate_enums():
    """Add new enum values to ServiceStatus and RequestStatus."""
    print("🔄 بدء تحديث enum types...")
    
    async with engine.begin() as conn:
        try:
            # Check if PENDING already exists in servicestatus
            result = await conn.execute(text("""
                SELECT unnest(enum_range(NULL::servicestatus))::text AS enum_value
            """))
            existing_values = [row[0] for row in result.fetchall()]
            
            print(f"القيم الحالية في servicestatus: {existing_values}")
            
            # PostgreSQL doesn't support IF NOT EXISTS for ALTER TYPE ADD VALUE
            # So we need to check first and catch the error if it exists
            try:
                if 'pending' not in existing_values:
                    print("📝 إضافة 'pending' إلى servicestatus...")
                    await conn.execute(text("ALTER TYPE servicestatus ADD VALUE 'pending'"))
                    print("✅ تم إضافة 'pending'")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print("ℹ️ 'pending' موجود بالفعل في servicestatus")
                else:
                    raise
            
            try:
                if 'rejected' not in existing_values:
                    print("📝 إضافة 'rejected' إلى servicestatus...")
                    await conn.execute(text("ALTER TYPE servicestatus ADD VALUE 'rejected'"))
                    print("✅ تم إضافة 'rejected'")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print("ℹ️ 'rejected' موجود بالفعل في servicestatus")
                else:
                    raise
            
            # Check RequestStatus enum
            result = await conn.execute(text("""
                SELECT unnest(enum_range(NULL::requeststatus))::text AS enum_value
            """))
            existing_values = [row[0] for row in result.fetchall()]
            
            print(f"القيم الحالية في requeststatus: {existing_values}")
            
            try:
                if 'pending' not in existing_values:
                    print("📝 إضافة 'pending' إلى requeststatus...")
                    await conn.execute(text("ALTER TYPE requeststatus ADD VALUE 'pending'"))
                    print("✅ تم إضافة 'pending'")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print("ℹ️ 'pending' موجود بالفعل في requeststatus")
                else:
                    raise
            
            try:
                if 'rejected' not in existing_values:
                    print("📝 إضافة 'rejected' إلى requeststatus...")
                    await conn.execute(text("ALTER TYPE requeststatus ADD VALUE 'rejected'"))
                    print("✅ تم إضافة 'rejected'")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print("ℹ️ 'rejected' موجود بالفعل في requeststatus")
                else:
                    raise
            
            print("\n✅ تم تحديث enum types بنجاح!")
            
        except Exception as e:
            print(f"❌ خطأ أثناء التحديث: {e}")
            print("\nيمكنك تشغيل هذه الأوامر يدوياً في PostgreSQL:")
            print("ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'pending';")
            print("ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'rejected';")
            print("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'pending';")
            print("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'rejected';")


if __name__ == "__main__":
    asyncio.run(migrate_enums())

