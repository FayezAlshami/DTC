"""Complete database setup script - runs all migrations in correct order."""
import asyncio
import subprocess
import sys
import os

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

MIGRATIONS = [
    ("setup_database.py", "إنشاء الجداول الأساسية"),
    ("migrate_enums.py", "إضافة enum values"),
    ("migrate_specializations.py", "إنشاء جدول الاختصاصات"),
    ("migrate_telegram_id.py", "تحديث telegram_id إلى BIGINT"),
    ("migrate_add_preferred_gender.py", "إضافة عمود preferred_gender"),
    ("migrate_contact_accounts.py", "إنشاء جدول حسابات التواصل"),
    ("migrate_add_email_verified.py", "إضافة عمود email_verified"),
    ("migrate_add_teacher_tables.py", "إضافة نظام الأساتذة والمواد"),
    ("migrate_enum_data.py", "تحديث بيانات enum"),
]

async def run_migration(script, description):
    """Run a migration script."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"📄 الملف: {script}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr and result.returncode != 0:
            print(f"⚠️  Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode != 0:
            print(f"\n❌ فشل في {script}")
            return False
        
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ انتهت مهلة الانتظار لـ {script}")
        return False
    except Exception as e:
        print(f"❌ خطأ في تشغيل {script}: {e}")
        return False

async def main():
    """Run all migrations in order."""
    print("="*60)
    print("🚀 بدء إعداد قاعدة البيانات الكاملة")
    print("="*60)
    
    failed = []
    for script, description in MIGRATIONS:
        if not os.path.exists(script):
            print(f"\n⚠️  الملف {script} غير موجود. تخطي...")
            continue
        
        success = await run_migration(script, description)
        if not success:
            failed.append((script, description))
            print(f"\n⚠️  فشل في {script}. هل تريد المتابعة؟ (y/n)")
            # Continue anyway for now
    
    print("\n" + "="*60)
    if failed:
        print("⚠️  اكتمل الإعداد مع بعض الأخطاء:")
        for script, desc in failed:
            print(f"   - {script}: {desc}")
    else:
        print("🎉 تم إعداد قاعدة البيانات بنجاح!")
    print("="*60)
    
    print("\n📋 ملخص الجداول المنشأة:")
    print("   - users (المستخدمون)")
    print("   - verification_codes (أكواد التحقق)")
    print("   - services (الخدمات)")
    print("   - service_requests (طلبات الخدمات)")
    print("   - contact_requests (طلبات التواصل)")
    print("   - admin_logs (سجلات الإدارة)")
    print("   - specializations (الاختصاصات)")
    print("   - contact_accounts (حسابات التواصل)")
    print("   - subjects (المواد الدراسية)")
    print("   - teacher_specializations (ربط الأساتذة بالاختصاصات)")
    print("   - teacher_subjects (ربط الأساتذة بالمواد)")

if __name__ == "__main__":
    asyncio.run(main())

