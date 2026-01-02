"""Migration script to create assignments table."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def create_assignments_table():
    """Create assignments table."""
    print("\n🔄 إنشاء جدول الوظائف (assignments)...")
    
    async with engine.begin() as conn:
        try:
            # Check if table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'assignments'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                # Create table
                await conn.execute(text("""
                    CREATE TABLE assignments (
                        id SERIAL PRIMARY KEY,
                        teacher_subject_id INTEGER NOT NULL REFERENCES teacher_subjects(id) ON DELETE CASCADE,
                        title VARCHAR(255) NULL,
                        description TEXT NULL,
                        file_id VARCHAR(500) NOT NULL,
                        file_type VARCHAR(50) NOT NULL,
                        file_name VARCHAR(500) NULL,
                        file_size INTEGER NULL,
                        display_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))
                
                # Create indexes separately
                await conn.execute(text("""
                    CREATE INDEX idx_assignments_teacher_subject_id ON assignments(teacher_subject_id)
                """))
                
                await conn.execute(text("""
                    CREATE INDEX idx_assignments_display_order ON assignments(teacher_subject_id, display_order)
                """))
                
                print("✅ تم إنشاء جدول assignments")
            else:
                print("✅ جدول assignments موجود بالفعل")
                
        except Exception as e:
            print(f"❌ خطأ في إنشاء جدول assignments: {e}")
            raise


async def main():
    """Run migration."""
    print("=" * 60)
    print("🚀 بدء migration لجدول الوظائف")
    print("=" * 60)
    
    try:
        await create_assignments_table()
        print("\n✅ تم إكمال migration بنجاح!")
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء migration: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

