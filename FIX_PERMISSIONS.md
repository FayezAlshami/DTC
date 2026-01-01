# إصلاح مشكلة الصلاحيات في قاعدة البيانات

## المشكلة
المستخدم `fayez` لا يملك صلاحيات كافية لإنشاء enum types وجداول في schema `public`.

## الحل

### الطريقة الأولى: استخدام psql (موصى بها)

1. **اتصل بقاعدة البيانات كمستخدم postgres (superuser):**

   **إذا واجهت خطأ Peer authentication:**
   ```bash
   # استخدم TCP/IP بدلاً من Unix socket
   psql -h localhost -U postgres -d dtc
   ```
   
   **أو استخدم sudo:**
   ```bash
   sudo -u postgres psql -d dtc
   ```
   
   **أو استخدم PGPASSWORD:**
   ```bash
   PGPASSWORD="your_password" psql -h localhost -U postgres -d dtc
   ```

2. **شغّل الأوامر التالية:**
   ```sql
   -- منح الصلاحيات الأساسية
   GRANT USAGE ON SCHEMA public TO fayez;
   GRANT CREATE ON SCHEMA public TO fayez;
   GRANT ALL PRIVILEGES ON DATABASE dtc TO fayez;
   
   -- منح الصلاحيات على الجداول الموجودة
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fayez;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fayez;
   
   -- منح الصلاحيات على الكائنات المستقبلية
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO fayez;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO fayez;
   ```

3. **أو استخدم الملف المرفق:**
   ```bash
   psql -U postgres -d dtc -f grant_permissions.sql
   ```

### الطريقة الثانية: استخدام Python script

```bash
python fix_permissions.py
```

**ملاحظة:** ستحتاج إلى كلمة مرور postgres عند تشغيل هذا السكريبت.

### الطريقة الثالثة: جعل المستخدم owner للـ schema (أقوى)

```sql
ALTER SCHEMA public OWNER TO fayez;
```

## بعد إعطاء الصلاحيات

بعد إعطاء الصلاحيات، شغّل migrations مرة أخرى:

```bash
python setup_complete_database.py
```

أو شغّل كل migration على حدة:

```bash
python setup_database.py
python migrate_enums.py
python migrate_specializations.py
python migrate_add_preferred_gender.py
python migrate_contact_accounts.py
python migrate_add_email_verified.py
python migrate_add_teacher_tables.py
python migrate_enum_data.py
```

## التحقق من الصلاحيات

للتحقق من الصلاحيات الحالية:

```sql
-- في psql
\du fayez
\dn+ public
```

