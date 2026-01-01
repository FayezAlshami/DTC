# إصلاح سريع لمشاكل قاعدة البيانات

## المشاكل الحالية

1. ❌ **صلاحيات غير كافية**: المستخدم `fayez` لا يملك صلاحيات لإنشاء enum types
2. ❌ **جداول غير موجودة**: بعض الجداول لم يتم إنشاؤها بسبب مشاكل الصلاحيات

## الحل السريع (3 خطوات)

### الخطوة 1: إعطاء الصلاحيات

اتصل بقاعدة البيانات كمستخدم `postgres`:

```bash
psql -U postgres -d dtc
```

ثم شغّل:

```sql
GRANT USAGE ON SCHEMA public TO fayez;
GRANT CREATE ON SCHEMA public TO fayez;
GRANT ALL PRIVILEGES ON DATABASE dtc TO fayez;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fayez;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fayez;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO fayez;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO fayez;
```

أو استخدم الملف:

```bash
psql -U postgres -d dtc -f grant_permissions.sql
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

