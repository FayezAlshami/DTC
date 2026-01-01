"""Migration script to add teacher role and related tables."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def add_teacher_role():
    """Add TEACHER role to userrole enum."""
    print("🔄 إضافة دور TEACHER إلى enum...")
    
    async with engine.begin() as conn:
        try:
            # Check if TEACHER already exists in userrole enum
            result = await conn.execute(text("""
                SELECT unnest(enum_range(NULL::userrole))::text AS enum_value
            """))
            existing_values = [row[0] for row in result.fetchall()]
            
            print(f"القيم الحالية في userrole: {existing_values}")
            
            if 'TEACHER' not in existing_values:
                print("📝 إضافة 'TEACHER' إلى userrole...")
                await conn.execute(text("ALTER TYPE userrole ADD VALUE 'TEACHER'"))
                print("✅ تم إضافة 'TEACHER'")
            else:
                print("✅ 'TEACHER' موجود بالفعل")
                
        except Exception as e:
            print(f"⚠️ خطأ في إضافة TEACHER role: {e}")


async def create_subjects_table():
    """Create subjects table."""
    print("\n🔄 إنشاء جدول المواد (subjects)...")
    
    async with engine.begin() as conn:
        try:
            # Check if table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'subjects'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                await conn.execute(text("""
                    CREATE TABLE subjects (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        code VARCHAR(50) UNIQUE,
                        description TEXT,
                        specialization_id INTEGER NOT NULL REFERENCES specializations(id) ON DELETE CASCADE,
                        credit_hours INTEGER,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        display_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX idx_subjects_name ON subjects(name);
                    CREATE INDEX idx_subjects_specialization_id ON subjects(specialization_id);
                """))
                print("✅ تم إنشاء جدول subjects")
            else:
                print("✅ جدول subjects موجود بالفعل")
                
        except Exception as e:
            print(f"❌ خطأ في إنشاء جدول subjects: {e}")


async def create_teacher_specializations_table():
    """Create teacher_specializations table."""
    print("\n🔄 إنشاء جدول ربط الأساتذة بالاختصاصات (teacher_specializations)...")
    
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'teacher_specializations'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                await conn.execute(text("""
                    CREATE TABLE teacher_specializations (
                        id SERIAL PRIMARY KEY,
                        teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        specialization_id INTEGER NOT NULL REFERENCES specializations(id) ON DELETE CASCADE,
                        is_primary BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(teacher_id, specialization_id)
                    );
                    CREATE INDEX idx_teacher_specializations_teacher_id ON teacher_specializations(teacher_id);
                    CREATE INDEX idx_teacher_specializations_specialization_id ON teacher_specializations(specialization_id);
                """))
                print("✅ تم إنشاء جدول teacher_specializations")
            else:
                print("✅ جدول teacher_specializations موجود بالفعل")
                
        except Exception as e:
            print(f"❌ خطأ في إنشاء جدول teacher_specializations: {e}")


async def create_teacher_subjects_table():
    """Create teacher_subjects table."""
    print("\n🔄 إنشاء جدول ربط الأساتذة بالمواد (teacher_subjects)...")
    
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'teacher_subjects'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                await conn.execute(text("""
                    CREATE TABLE teacher_subjects (
                        id SERIAL PRIMARY KEY,
                        teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                        academic_year VARCHAR(20),
                        semester VARCHAR(20),
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(teacher_id, subject_id, academic_year, semester)
                    );
                    CREATE INDEX idx_teacher_subjects_teacher_id ON teacher_subjects(teacher_id);
                    CREATE INDEX idx_teacher_subjects_subject_id ON teacher_subjects(subject_id);
                """))
                print("✅ تم إنشاء جدول teacher_subjects")
            else:
                print("✅ جدول teacher_subjects موجود بالفعل")
                
        except Exception as e:
            print(f"❌ خطأ في إنشاء جدول teacher_subjects: {e}")


async def main():
    """Run all migrations."""
    print("=" * 60)
    print("🚀 بدء migration لإضافة نظام الأساتذة والمواد")
    print("=" * 60)
    
    try:
        await add_teacher_role()
        await create_subjects_table()
        await create_teacher_specializations_table()
        await create_teacher_subjects_table()
        
        print("\n" + "=" * 60)
        print("🎉 تم إكمال migration بنجاح!")
        print("=" * 60)
        print("\n📋 الجداول المضافة:")
        print("   - subjects: جدول المواد الدراسية")
        print("   - teacher_specializations: ربط الأساتذة بالاختصاصات")
        print("   - teacher_subjects: ربط الأساتذة بالمواد")
        print("\n📋 التعديلات:")
        print("   - إضافة دور TEACHER إلى userrole enum")
        
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء migration: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

