"""Migration script to remove STUDENT role and update users to USER role."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def migrate_student_to_user():
    """Update all users with STUDENT role to USER role."""
    print("\n🔄 تحديث دور STUDENT إلى USER...")
    
    async with engine.begin() as conn:
        try:
            # Check if there are any users with STUDENT role
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM users 
                WHERE role = 'STUDENT'
            """))
            student_count = result.scalar()
            
            if student_count > 0:
                print(f"📝 تم العثور على {student_count} مستخدم بدور STUDENT")
                
                # Update all STUDENT users to USER
                await conn.execute(text("""
                    UPDATE users 
                    SET role = 'USER' 
                    WHERE role = 'STUDENT'
                """))
                
                print(f"✅ تم تحديث {student_count} مستخدم من STUDENT إلى USER")
            else:
                print("✅ لا يوجد مستخدمون بدور STUDENT")
            
            # Note: We don't remove STUDENT from enum because PostgreSQL doesn't support
            # removing enum values easily. The enum value will remain but won't be used.
            # If you want to remove it completely, you'll need to recreate the enum type.
            
        except Exception as e:
            print(f"❌ خطأ في تحديث دور STUDENT: {e}")
            raise


async def main():
    """Run migration."""
    print("=" * 60)
    print("🚀 بدء migration لإزالة دور STUDENT")
    print("=" * 60)
    
    try:
        await migrate_student_to_user()
        print("\n✅ تم إكمال migration بنجاح!")
        print("\n⚠️  ملاحظة: STUDENT لا يزال موجوداً في enum في قاعدة البيانات")
        print("   لكن لن يتم استخدامه بعد الآن. جميع الطلاب الآن لديهم role = USER")
        print("   و is_student = TRUE")
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء migration: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

