"""Script to grant database permissions - must be run as postgres superuser."""
import asyncio
import asyncpg
from config import config

async def grant_permissions():
    """Grant necessary permissions to database user."""
    print("🔐 إعطاء الصلاحيات للمستخدم...")
    print("⚠️  يجب تشغيل هذا السكريبت كمستخدم postgres (superuser)")
    
    # Connect as postgres superuser
    conn = await asyncpg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user="postgres",  # Use postgres superuser
        password=input("أدخل كلمة مرور postgres: ")  # You might want to use environment variable
    )
    
    try:
        print(f"\n📝 منح الصلاحيات للمستخدم: {config.DB_USER}")
        
        # Grant usage on schema
        await conn.execute("GRANT USAGE ON SCHEMA public TO $1", config.DB_USER)
        print("✅ تم منح USAGE على schema public")
        
        # Grant create privileges
        await conn.execute("GRANT CREATE ON SCHEMA public TO $1", config.DB_USER)
        print("✅ تم منح CREATE على schema public")
        
        # Grant all privileges on database
        await conn.execute(f"GRANT ALL PRIVILEGES ON DATABASE {config.DB_NAME} TO {config.DB_USER}")
        print(f"✅ تم منح ALL PRIVILEGES على قاعدة البيانات {config.DB_NAME}")
        
        # Grant all privileges on all existing tables
        await conn.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $1", config.DB_USER)
        print("✅ تم منح ALL PRIVILEGES على جميع الجداول")
        
        # Grant all privileges on all sequences
        await conn.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $1", config.DB_USER)
        print("✅ تم منح ALL PRIVILEGES على جميع Sequences")
        
        # Set default privileges for future objects
        await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {config.DB_USER}")
        await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {config.DB_USER}")
        print("✅ تم تعيين الصلاحيات الافتراضية للكائنات المستقبلية")
        
        print("\n🎉 تم منح الصلاحيات بنجاح!")
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        print("\n💡 يمكنك تشغيل الأوامر يدوياً في psql:")
        print(f"   GRANT USAGE ON SCHEMA public TO {config.DB_USER};")
        print(f"   GRANT CREATE ON SCHEMA public TO {config.DB_USER};")
        print(f"   GRANT ALL PRIVILEGES ON DATABASE {config.DB_NAME} TO {config.DB_USER};")
        print(f"   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {config.DB_USER};")
        print(f"   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {config.DB_USER};")
        print(f"   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {config.DB_USER};")
        print(f"   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {config.DB_USER};")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(grant_permissions())

