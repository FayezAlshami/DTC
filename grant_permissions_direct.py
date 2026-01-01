"""Direct script to grant database permissions using asyncpg."""
import asyncio
import asyncpg
from config import config

async def grant_permissions():
    """Grant necessary permissions to database user."""
    print("🔐 إعطاء الصلاحيات للمستخدم...")
    print(f"📋 قاعدة البيانات: {config.DB_NAME}")
    print(f"📋 المستخدم: {config.DB_USER}")
    print("")
    
    # Try to connect as postgres superuser
    # First, try to get postgres password from environment or ask user
    import os
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    
    if not postgres_password:
        print("⚠️  لم يتم العثور على POSTGRES_PASSWORD في البيئة")
        print("💡 يمكنك تعيينه: export POSTGRES_PASSWORD='your_password'")
        postgres_password = input("أدخل كلمة مرور postgres (أو اضغط Enter للخروج): ").strip()
        if not postgres_password:
            print("❌ تم الإلغاء")
            return
    
    try:
        print("🔄 الاتصال بقاعدة البيانات...")
        conn = await asyncpg.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user="postgres",
            password=postgres_password
        )
        
        print("✅ تم الاتصال بنجاح\n")
        
        try:
            print(f"📝 منح الصلاحيات للمستخدم: {config.DB_USER}")
            
            # Grant usage on schema
            await conn.execute("GRANT USAGE ON SCHEMA public TO $1", config.DB_USER)
            print("  ✅ تم منح USAGE على schema public")
            
            # Grant create privileges
            await conn.execute("GRANT CREATE ON SCHEMA public TO $1", config.DB_USER)
            print("  ✅ تم منح CREATE على schema public")
            
            # Grant all privileges on database
            await conn.execute(f"GRANT ALL PRIVILEGES ON DATABASE {config.DB_NAME} TO {config.DB_USER}")
            print(f"  ✅ تم منح ALL PRIVILEGES على قاعدة البيانات {config.DB_NAME}")
            
            # Grant all privileges on all existing tables
            await conn.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $1", config.DB_USER)
            print("  ✅ تم منح ALL PRIVILEGES على جميع الجداول")
            
            # Grant all privileges on all sequences
            await conn.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $1", config.DB_USER)
            print("  ✅ تم منح ALL PRIVILEGES على جميع Sequences")
            
            # Set default privileges for future objects
            await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {config.DB_USER}")
            await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {config.DB_USER}")
            print("  ✅ تم تعيين الصلاحيات الافتراضية للكائنات المستقبلية")
            
            print("\n🎉 تم منح الصلاحيات بنجاح!")
            print("\n💡 الآن يمكنك تشغيل:")
            print("   python setup_complete_database.py")
            
        except Exception as e:
            print(f"\n❌ خطأ أثناء منح الصلاحيات: {e}")
            print("\n💡 يمكنك تشغيل الأوامر يدوياً في psql:")
            print(f"   psql -h localhost -U postgres -d {config.DB_NAME}")
            print(f"   ثم شغّل الأوامر من ملف grant_permissions.sql")
            raise
            
        finally:
            await conn.close()
            
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ كلمة المرور غير صحيحة")
        print("💡 حاول مرة أخرى أو استخدم:")
        print("   export POSTGRES_PASSWORD='your_password'")
        print("   python grant_permissions_direct.py")
    except Exception as e:
        print(f"\n❌ خطأ في الاتصال: {e}")
        print("\n💡 بدائل:")
        print("   1. استخدم sudo: sudo -u postgres psql -d dtc")
        print("   2. استخدم TCP/IP: psql -h localhost -U postgres -d dtc")
        print("   3. استخدم PGPASSWORD: PGPASSWORD='pass' psql -h localhost -U postgres -d dtc")

if __name__ == "__main__":
    asyncio.run(grant_permissions())

