"""Migration script to create assignment_submissions table."""
import asyncio
from sqlalchemy import text
from database.base import engine


async def create_assignment_submissions_table():
    """Create assignment_submissions table."""
    print("\n🔄 إنشاء جدول حلول الوظائف (assignment_submissions)...")
    
    async with engine.begin() as conn:
        try:
            # Check if table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'assignment_submissions'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                # Create table
                await conn.execute(text("""
                    CREATE TABLE assignment_submissions (
                        id SERIAL PRIMARY KEY,
                        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
                        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                        file_id VARCHAR(500) NOT NULL,
                        file_type VARCHAR(50) NOT NULL,
                        file_name VARCHAR(500) NULL,
                        file_size INTEGER NULL,
                        notes TEXT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))
                
                # Create indexes separately
                await conn.execute(text("""
                    CREATE INDEX idx_assignment_submissions_student_id ON assignment_submissions(student_id)
                """))
                
                await conn.execute(text("""
                    CREATE INDEX idx_assignment_submissions_assignment_id ON assignment_submissions(assignment_id)
                """))
                
                await conn.execute(text("""
                    CREATE INDEX idx_assignment_submissions_subject_id ON assignment_submissions(subject_id)
                """))
                
                print("✅ تم إنشاء جدول assignment_submissions بنجاح!")
            else:
                print("ℹ️  جدول assignment_submissions موجود بالفعل.")
                
        except Exception as e:
            print(f"❌ حدث خطأ أثناء إنشاء الجدول: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(create_assignment_submissions_table())

