# إصلاح خطأ Enum في قاعدة البيانات

## المشكلة
```
invalid input value for enum servicestatus: "PENDING"
```

هذا يعني أن قاعدة البيانات لا تحتوي على القيم الجديدة `pending` و `rejected` في enum types.

## الحل السريع

### الطريقة 1: استخدام ملف SQL (الأسهل)

1. افتح **pgAdmin** أو **psql**
2. شغّل ملف `update_enums.sql`:
   ```sql
   ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'pending';
   ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'rejected';
   ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'pending';
   ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'rejected';
   ```

### الطريقة 2: استخدام Python Script

شغّل هذا الأمر في terminal:
```bash
python migrate_enums.py
```

### الطريقة 3: يدوياً في PostgreSQL

افتح **psql** أو **pgAdmin Query Tool** وشغّل:

```sql
-- إضافة القيم الجديدة لـ servicestatus
ALTER TYPE servicestatus ADD VALUE 'pending';
ALTER TYPE servicestatus ADD VALUE 'rejected';

-- إضافة القيم الجديدة لـ requeststatus
ALTER TYPE requeststatus ADD VALUE 'pending';
ALTER TYPE requeststatus ADD VALUE 'rejected';
```

**ملاحظة**: إذا ظهرت رسالة خطأ "already exists" فهذا يعني أن القيمة موجودة بالفعل، وهذا جيد.

## التحقق من النجاح

بعد تشغيل الأوامر، تحقق من القيم:

```sql
SELECT unnest(enum_range(NULL::servicestatus))::text AS servicestatus_values;
SELECT unnest(enum_range(NULL::requeststatus))::text AS requeststatus_values;
```

يجب أن ترى القيم التالية:
- servicestatus: draft, pending, published, removed, completed, contact_accepted, expired, rejected
- requeststatus: draft, pending, published, removed, completed, contact_accepted, expired, rejected

## بعد الإصلاح

بعد تحديث enum types، أعد تشغيل:
- البوت: `python main.py`
- الويب داش بورد: `python web_dashboard.py`

