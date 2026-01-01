"""Migration script to add email_verified column to users table."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def add_email_verified_column():
    """Add email_verified column to users table."""
    print("🔄 بدء إضافة عمود email_verified...")
    
    async with engine.begin() as conn:
        try:
            # Check if column already exists
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'email_verified'
            """))
            
            row = result.fetchone()
            if row:
                print("✅ عمود email_verified موجود بالفعل.")
            else:
                # Add column with default value False
                print("📝 إضافة عمود email_verified...")
                await conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE
                """))
                print("✅ تم إضافة عمود email_verified بنجاح!")
            
            # Update existing users: mark as verified if they have a used verification code
            print("\n📝 تحديث البيانات الموجودة...")
            result = await conn.execute(text("""
                UPDATE users 
                SET email_verified = TRUE
                WHERE id IN (
                    SELECT DISTINCT user_id 
                    FROM verification_codes 
                    WHERE is_used = TRUE
                )
            """))
            
            updated_count = result.rowcount if hasattr(result, 'rowcount') else 0
            print(f"✅ تم تحديث {updated_count} مستخدم كـ verified بناءً على وجود verification codes مستخدمة.")
            
            print("\n" + "=" * 60)
            print("🎉 تم تحديث قاعدة البيانات بنجاح!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ خطأ أثناء التحديث: {e}")
            print("\n💡 يمكنك تشغيل هذا الأمر يدوياً في PostgreSQL:")
            print("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE;")
            print("UPDATE users SET email_verified = TRUE WHERE id IN (SELECT DISTINCT user_id FROM verification_codes WHERE is_used = TRUE);")
            raise


async def main():
    """Main function."""
    await add_email_verified_column()


if __name__ == "__main__":
    asyncio.run(main())

