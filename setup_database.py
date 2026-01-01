"""Script to setup database tables."""
import asyncio
from database.base import init_db

async def setup():
    """Initialize database tables."""
    print("🚀 بدء إعداد قاعدة البيانات...")
    try:
        await init_db()
        print("✅ تم إنشاء الجداول بنجاح!")
        print("\nالجداول المنشأة:")
        print("  - users")
        print("  - verification_codes")
        print("  - services")
        print("  - service_requests")
        print("  - contact_requests")
        print("  - admin_logs")
    except Exception as e:
        print(f"❌ خطأ في إعداد قاعدة البيانات: {e}")
        print("\nتأكد من:")
        print("  1. تشغيل PostgreSQL")
        print("  2. صحة إعدادات قاعدة البيانات في config.py أو .env")
        print("  3. وجود قاعدة البيانات dtc_job_bot")

if __name__ == "__main__":
    asyncio.run(setup())

