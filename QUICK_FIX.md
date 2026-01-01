# إصلاح سريع لمشاكل قاعدة البيانات

## المشاكل الحالية

1. ❌ **صلاحيات غير كافية**: المستخدم `fayez` لا يملك صلاحيات لإنشاء enum types
2. ❌ **جداول غير موجودة**: بعض الجداول لم يتم إنشاؤها بسبب مشاكل الصلاحيات

## الحل السريع (3 خطوات)

### الخطوة 1: إعطاء الصلاحيات

**الطريقة الأولى: استخدام TCP/IP (موصى بها)**

```bash
psql -h localhost -U postgres -d dtc
```

ثم أدخل كلمة مرور postgres وشغّل:

```sql
GRANT USAGE ON SCHEMA public TO fayez;
GRANT CREATE ON SCHEMA public TO fayez;
GRANT ALL PRIVILEGES ON DATABASE dtc TO fayez;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fayez;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fayez;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO fayez;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO fayez;
```

**الطريقة الثانية: استخدام sudo**

```bash
sudo -u postgres psql -d dtc
```

ثم شغّل نفس الأوامر SQL أعلاه.

**الطريقة الثالثة: استخدام السكريبت**

```bash
chmod +x grant_permissions.sh
./grant_permissions.sh
```

أو مع كلمة المرور:

```bash
./grant_permissions.sh "your_postgres_password"
```

**الطريقة الرابعة: استخدام PGPASSWORD**

```bash
PGPASSWORD="your_postgres_password" psql -h localhost -U postgres -d dtc -f grant_permissions.sql
```

**الطريقة الخامسة: استخدام Python Script (أسهل)**

```bash
# مع كلمة المرور في البيئة
export POSTGRES_PASSWORD="your_postgres_password"
python grant_permissions_direct.py

# أو بدون export (سيطلب منك إدخالها)
python grant_permissions_direct.py
```

### الخطوة 2: إعادة تشغيل Migrations

```bash
python setup_complete_database.py
```

### الخطوة 3: التحقق

تحقق من أن جميع الجداول تم إنشاؤها:

```bash
psql -U fayez -d dtc -c "\dt"
```

## إذا استمرت المشاكل

راجع ملف `FIX_PERMISSIONS.md` للحلول التفصيلية.

