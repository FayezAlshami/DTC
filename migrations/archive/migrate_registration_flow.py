"""Migration script to add new fields for the updated registration flow."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def add_visitor_role():
    """Add VISITOR role to userrole enum."""
    print("🔄 إضافة دور VISITOR إلى enum...")
    
    async with engine.begin() as conn:
        try:
            # Check if VISITOR already exists in userrole enum
            result = await conn.execute(text("""
                SELECT unnest(enum_range(NULL::userrole))::text AS enum_value
            """))
            existing_values = [row[0] for row in result.fetchall()]
            
            print(f"القيم الحالية في userrole: {existing_values}")
            
            if 'VISITOR' not in existing_values:
                print("📝 إضافة 'VISITOR' إلى userrole...")
                await conn.execute(text("ALTER TYPE userrole ADD VALUE 'VISITOR'"))
                print("✅ تم إضافة 'VISITOR'")
            else:
                print("✅ 'VISITOR' موجود بالفعل")
                
        except Exception as e:
            print(f"⚠️ خطأ في إضافة VISITOR role: {e}")


async def add_new_user_columns():
    """Add new columns to users table."""
    print("\n🔄 إضافة أعمدة جديدة إلى جدول users...")
    
    columns_to_add = [
        ("teacher_number", "VARCHAR(100)", "رقم الأستاذ"),
        ("visitor_number", "VARCHAR(100)", "رقم الزائر"),
        ("specialization_id", "INTEGER REFERENCES specializations(id)", "معرف التخصص"),
    ]
    
    async with engine.begin() as conn:
        for column_name, column_type, description in columns_to_add:
            try:
                # Check if column exists
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                        AND column_name = '{column_name}'
                    );
                """))
                column_exists = result.scalar()
                
                if not column_exists:
                    print(f"📝 إضافة عمود {column_name} ({description})...")
                    await conn.execute(text(f"""
                        ALTER TABLE users ADD COLUMN {column_name} {column_type}
                    """))
                    print(f"✅ تم إضافة عمود {column_name}")
                else:
                    print(f"✅ عمود {column_name} موجود بالفعل")
                    
            except Exception as e:
                print(f"⚠️ خطأ في إضافة عمود {column_name}: {e}")


async def create_specialization_index():
    """Create index on specialization_id column."""
    print("\n🔄 إنشاء index على عمود specialization_id...")
    
    async with engine.begin() as conn:
        try:
            # Check if index exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE tablename = 'users' 
                    AND indexname = 'idx_users_specialization_id'
                );
            """))
            index_exists = result.scalar()
            
            if not index_exists:
                await conn.execute(text("""
                    CREATE INDEX idx_users_specialization_id ON users(specialization_id)
                """))
                print("✅ تم إنشاء index")
            else:
                print("✅ index موجود بالفعل")
                
        except Exception as e:
            print(f"⚠️ خطأ في إنشاء index: {e}")


async def main():
    """Run all migrations."""
    print("=" * 60)
    print("🚀 بدء migration لتحديث نظام التسجيل")
    print("=" * 60)
    
    try:
        await add_visitor_role()
        await add_new_user_columns()
        await create_specialization_index()
        
        print("\n" + "=" * 60)
        print("🎉 تم إكمال migration بنجاح!")
        print("=" * 60)
        print("\n📋 التغييرات:")
        print("   - إضافة دور VISITOR إلى userrole enum")
        print("   - إضافة عمود teacher_number إلى جدول users")
        print("   - إضافة عمود visitor_number إلى جدول users")
        print("   - إضافة عمود specialization_id إلى جدول users")
        
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء migration: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

