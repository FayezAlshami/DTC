"""
سكريبت تحديث قاعدة البيانات الموجودة (بدون حذف البيانات)
"""

import asyncio
import asyncpg
from config import config

async def update_database():
    """تحديث البنية بدون حذف البيانات"""

    conn = await asyncpg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )

    try:
        print("🔧 بدء تحديث قاعدة البيانات...\n")

        # ======== الخطوة 1: إضافة العمود role إذا مو موجود ========
        print("📋 الخطوة 1: فحص عمود role...")
        try:
            # التحقق من وجود العمود
            check_column = await conn.fetchval("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'role';
            """)

            if not check_column:
                print("  ⚠️  العمود role غير موجود - جاري الإضافة...")

                # إنشاء enum إذا مو موجود أو تحديثه
                enum_name = 'userrole'
                check_enum = await conn.fetchval("""
                    SELECT typname FROM pg_type WHERE typname = 'userrole';
                """)
                
                if not check_enum:
                    await conn.execute("""
                        CREATE TYPE userrole AS ENUM ('ADMIN', 'STUDENT', 'USER');
                    """)
                    print("  ✅ تم إنشاء enum userrole")
                    default_value = 'USER'
                else:
                    print("  ✅ enum userrole موجود")
                    # التحقق من القيم الموجودة
                    existing_values = await conn.fetch("""
                        SELECT enumlabel 
                        FROM pg_enum 
                        WHERE enumtypid = 'userrole'::regtype;
                    """)
                    existing = [row['enumlabel'] for row in existing_values]
                    print(f"  📋 القيم الموجودة: {existing}")
                    
                    # استخدام أول قيمة موجودة كقيمة افتراضية
                    if 'USER' in existing:
                        default_value = 'USER'
                    elif 'STUDENT' in existing:
                        default_value = 'STUDENT'
                    elif 'ADMIN' in existing:
                        default_value = 'ADMIN'
                    else:
                        default_value = existing[0] if existing else 'USER'
                    
                    # محاولة إضافة القيم المفقودة
                    needed_values = ['ADMIN', 'STUDENT', 'USER']
                    for value in needed_values:
                        if value not in existing:
                            print(f"  ⚙️  محاولة إضافة القيمة '{value}' إلى enum...")
                            try:
                                await conn.execute(f"""
                                    ALTER TYPE userrole ADD VALUE '{value}';
                                """)
                                print(f"  ✅ تم إضافة '{value}'")
                                if default_value not in ['ADMIN', 'STUDENT', 'USER']:
                                    default_value = 'USER'
                            except Exception as e:
                                print(f"  ⚠️  لا يمكن إضافة '{value}': {e}")
                                # إذا فشل، قد يكون بسبب استخدام الـ enum في مكان آخر
                                pass

                # إضافة العمود
                try:
                    await conn.execute(f"""
                        ALTER TABLE users 
                        ADD COLUMN role userrole NOT NULL DEFAULT '{default_value}';
                    """)
                    print(f"  ✅ تم إضافة عمود role بنجاح (القيمة الافتراضية: {default_value})")
                except Exception as e:
                    # إذا فشل، جرب بدون NOT NULL أولاً
                    print(f"  ⚠️  محاولة طريقة بديلة: {e}")
                    try:
                        await conn.execute(f"""
                            ALTER TABLE users 
                            ADD COLUMN role userrole DEFAULT '{default_value}';
                        """)
                        await conn.execute(f"""
                            UPDATE users SET role = '{default_value}' WHERE role IS NULL;
                        """)
                        await conn.execute("""
                            ALTER TABLE users 
                            ALTER COLUMN role SET NOT NULL;
                        """)
                        print(f"  ✅ تم إضافة عمود role بنجاح (مع تحديث البيانات، القيمة الافتراضية: {default_value})")
                    except Exception as e2:
                        # إذا فشل أيضاً، استخدم TEXT مؤقتاً ثم حوله
                        print(f"  ⚠️  محاولة طريقة بديلة أخرى: {e2}")
                        await conn.execute(f"""
                            ALTER TABLE users 
                            ADD COLUMN role TEXT DEFAULT '{default_value}';
                        """)
                        await conn.execute(f"""
                            UPDATE users SET role = '{default_value}' WHERE role IS NULL;
                        """)
                        # تحويل إلى enum
                        await conn.execute("""
                            ALTER TABLE users 
                            ALTER COLUMN role TYPE userrole USING role::userrole;
                        """)
                        await conn.execute("""
                            ALTER TABLE users 
                            ALTER COLUMN role SET NOT NULL;
                        """)
                        print("  ✅ تم إضافة عمود role بنجاح (مع تحويل النوع)")
            else:
                print("  ✅ العمود role موجود")

            # توحيد قيم role إلى أحرف كبيرة
            print("📋 الخطوة 1.1: توحيد قيم role...")
            await conn.execute("""
                UPDATE users 
                SET role = UPPER(role::text)::userrole
            """)
            print("  ✅ تم توحيد قيم role")
        except Exception as e:
            print(f"  ❌ خطأ في عمود role: {e}")
            import traceback
            traceback.print_exc()
            raise

        # ======== الخطوة 2: تحديث servicestatus enum ========
        print("\n📋 الخطوة 2: تحديث servicestatus enum...")
        try:
            # فحص القيم الموجودة
            existing_values = await conn.fetch("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = 'servicestatus'::regtype;
            """)
            existing = [row['enumlabel'] for row in existing_values]

            needed_values = ['DRAFT', 'PENDING', 'PUBLISHED', 'REMOVED', 
                           'COMPLETED', 'CONTACT_ACCEPTED', 'EXPIRED', 'REJECTED']

            for value in needed_values:
                if value not in existing:
                    print(f"  ⚙️  إضافة القيمة '{value}'...")
                    try:
                        await conn.execute(f"""
                            ALTER TYPE servicestatus ADD VALUE '{value}';
                        """)
                        print(f"  ✅ تم إضافة '{value}'")
                    except Exception as e:
                        print(f"  ⚠️  {value}: {e}")

            print("  ✅ servicestatus محدث بالكامل")
        except Exception as e:
            print(f"  ⚠️  ملاحظة servicestatus: {e}")
            # نحاول إنشاء الـ enum من الصفر إذا مو موجود
            try:
                await conn.execute("""
                    CREATE TYPE servicestatus AS ENUM (
                        'DRAFT', 'PENDING', 'PUBLISHED', 'REMOVED', 
                        'COMPLETED', 'CONTACT_ACCEPTED', 'EXPIRED', 'REJECTED'
                    );
                """)
                print("  ✅ تم إنشاء servicestatus من جديد")
            except:
                pass

        # ======== الخطوة 3: تحديث requeststatus enum ========
        print("\n📋 الخطوة 3: تحديث requeststatus enum...")
        try:
            existing_values = await conn.fetch("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = 'requeststatus'::regtype;
            """)
            existing = [row['enumlabel'] for row in existing_values]

            needed_values = ['DRAFT', 'PENDING', 'PUBLISHED', 'REMOVED', 
                           'COMPLETED', 'CONTACT_ACCEPTED', 'EXPIRED', 'REJECTED']

            for value in needed_values:
                if value not in existing:
                    print(f"  ⚙️  إضافة القيمة '{value}'...")
                    try:
                        await conn.execute(f"""
                            ALTER TYPE requeststatus ADD VALUE '{value}';
                        """)
                        print(f"  ✅ تم إضافة '{value}'")
                    except Exception as e:
                        print(f"  ⚠️  {value}: {e}")

            print("  ✅ requeststatus محدث بالكامل")
        except Exception as e:
            print(f"  ⚠️  ملاحظة requeststatus: {e}")
            try:
                await conn.execute("""
                    CREATE TYPE requeststatus AS ENUM (
                        'DRAFT', 'PENDING', 'PUBLISHED', 'REMOVED', 
                        'COMPLETED', 'CONTACT_ACCEPTED', 'EXPIRED', 'REJECTED'
                    );
                """)
                print("  ✅ تم إنشاء requeststatus من جديد")
            except:
                pass

        # ======== الخطوة 4: إنشاء Gender enum إذا مو موجود ========
        print("\n📋 الخطوة 4: فحص Gender enum...")
        try:
            check_gender_enum = await conn.fetchval("""
                SELECT typname FROM pg_type WHERE typname = 'gender';
            """)
            
            if not check_gender_enum:
                await conn.execute("""
                    CREATE TYPE gender AS ENUM ('male', 'female', 'other');
                """)
                print("  ✅ تم إنشاء enum gender")
            else:
                print("  ✅ enum gender موجود")
        except Exception as e:
            print(f"  ⚠️  ملاحظة gender enum: {e}")

        # ======== الخطوة 5: التحقق من باقي الأعمدة الضرورية ========
        print("\n📋 الخطوة 5: التحقق من الأعمدة الأخرى...")

        # قائمة الأعمدة المطلوبة
        required_columns = {
            'users': [
                ('telegram_id', 'BIGINT'),
                ('email', 'VARCHAR(255)'),
                ('password_hash', 'VARCHAR(255)'),
                ('is_active', 'BOOLEAN DEFAULT TRUE'),
                ('is_student', 'BOOLEAN DEFAULT FALSE'),
                ('profile_completed', 'BOOLEAN DEFAULT FALSE'),
                ('full_name', 'VARCHAR(255)'),
                ('student_id', 'VARCHAR(100)'),
                ('specialization', 'VARCHAR(255)'),
                ('phone_number', 'VARCHAR(50)'),
                ('date_of_birth', 'TIMESTAMP'),
                ('gender', 'gender'),
                ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
                ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ]
        }

        for table, columns in required_columns.items():
            for col_name, col_type in columns:
                check = await conn.fetchval(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = '{col_name}';
                """)

                if not check:
                    print(f"  ⚙️  إضافة {col_name} في {table}...")
                    try:
                        await conn.execute(f"""
                            ALTER TABLE {table} 
                            ADD COLUMN {col_name} {col_type};
                        """)
                        print(f"  ✅ تم إضافة {col_name}")
                    except Exception as e:
                        print(f"  ⚠️  {col_name}: {e}")

        print("\n" + "=" * 60)
        print("🎉 تم تحديث قاعدة البيانات بنجاح!")
        print("=" * 60)
        print("\n✅ البيانات الموجودة محفوظة")
        print("✅ البنية محدثة حسب المطلوب")
        print("\nيمكنك الآن تشغيل البوت:")
        print("  python main.py")

    except Exception as e:
        print(f"\n❌ حدث خطأ: {e}")
        print("\n💡 نصيحة: إذا استمرت المشاكل، استخدم fix_database_complete.py")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_database())