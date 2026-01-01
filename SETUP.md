# دليل إعداد وتشغيل المشروع

## متطلبات النظام

1. **Python 3.10 أو أحدث**
2. **PostgreSQL 12 أو أحدث**
3. **Git** (اختياري)

---

## خطوات الإعداد

### 1. إنشاء قاعدة البيانات في PostgreSQL

#### الطريقة الأولى: باستخدام psql (سطر الأوامر)

```bash
# افتح PostgreSQL Command Line
psql -U postgres

# ثم نفذ الأوامر التالية:
CREATE DATABASE dtc_job_bot;
\q
```

#### الطريقة الثانية: باستخدام pgAdmin

1. افتح **pgAdmin**
2. انقر بزر الماوس الأيمن على **Databases**
3. اختر **Create** → **Database**
4. أدخل الاسم: `dtc_job_bot`
5. انقر **Save**

#### الطريقة الثالثة: باستخدام SQL Shell

```sql
CREATE DATABASE dtc_job_bot;
```

---

### 2. إعداد البيئة الافتراضية (Virtual Environment)

```bash
# في مجلد المشروع
python -m venv venv

# تفعيل البيئة الافتراضية
# على Windows:
venv\Scripts\activate

# على Linux/Mac:
source venv/bin/activate
```

---

### 3. تثبيت المكتبات المطلوبة

```bash
pip install -r requirements.txt
```

---

### 4. إعداد ملف البيئة (.env)

أنشئ ملف `.env` في المجلد الرئيسي للمشروع:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here

# Database Configuration (Local PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dtc_job_bot
DB_USER=postgres
DB_PASSWORD=your_postgres_password

# Email Configuration (Optional for testing)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com

# Telegram Channels (Optional for testing)
SERVICES_CHANNEL_ID=@your_services_channel
REQUESTS_CHANNEL_ID=@your_requests_channel

# Admin Configuration
ADMIN_USER_IDS=123456789,987654321

# Verification
VERIFICATION_CODE_EXPIRY_MINUTES=10
```

**ملاحظات مهمة:**
- استبدل `your_bot_token_here` برمز البوت من [@BotFather](https://t.me/botfather)
- استبدل `your_postgres_password` بكلمة مرور PostgreSQL
- للحصول على App Password من Gmail:
  1. اذهب إلى [Google Account Settings](https://myaccount.google.com/)
  2. Security → 2-Step Verification → App passwords
  3. أنشئ App Password جديد

---

### 5. إنشاء الجداول في قاعدة البيانات

المشروع سينشئ الجداول تلقائياً عند التشغيل الأول. إذا أردت إنشاءها يدوياً:

```python
# قم بتشغيل هذا الأمر في Python
python -c "from database.base import init_db; import asyncio; asyncio.run(init_db())"
```

---

## تشغيل المشروع

### الطريقة الأولى: تشغيل مباشر

```bash
# تأكد من تفعيل البيئة الافتراضية أولاً
python main.py
```

### الطريقة الثانية: باستخدام Python Module

```bash
python -m main
```

---

## التحقق من الإعداد

بعد تشغيل المشروع، يجب أن ترى رسائل مثل:

```
INFO - Initializing database...
INFO - Database initialized.
INFO - Bot starting...
```

---

## استكشاف الأخطاء

### خطأ: "could not connect to server"

**الحل:**
- تأكد من تشغيل PostgreSQL
- تحقق من إعدادات `DB_HOST` و `DB_PORT` في `.env`
- تأكد من صحة اسم المستخدم وكلمة المرور

### خطأ: "database does not exist"

**الحل:**
- أنشئ قاعدة البيانات كما هو موضح في الخطوة 1
- تأكد من اسم قاعدة البيانات في `.env` يطابق الاسم الذي أنشأته

### خطأ: "password authentication failed"

**الحل:**
- تحقق من كلمة مرور PostgreSQL في `.env`
- تأكد من أن المستخدم `postgres` موجود وله الصلاحيات اللازمة

### خطأ: "BOT_TOKEN is required"

**الحل:**
- تأكد من إضافة `BOT_TOKEN` في ملف `.env`
- احصل على رمز البوت من [@BotFather](https://t.me/botfather)

---

## هيكل قاعدة البيانات

المشروع سينشئ الجداول التالية تلقائياً:

- `users` - المستخدمون
- `verification_codes` - أكواد التحقق
- `services` - الخدمات المقدمة
- `service_requests` - طلبات الخدمات
- `contact_requests` - طلبات التواصل
- `admin_logs` - سجلات الإدارة

---

## نصائح إضافية

1. **للاختبار المحلي:** يمكنك ترك `SERVICES_CHANNEL_ID` و `REQUESTS_CHANNEL_ID` فارغة مؤقتاً
2. **للتطوير:** استخدم قاعدة بيانات منفصلة للاختبار
3. **للإنتاج:** استخدم متغيرات البيئة الآمنة ولا تضع كلمات المرور في الكود

---

## الدعم

إذا واجهت أي مشاكل، تحقق من:
1. سجلات الأخطاء في Terminal
2. إعدادات قاعدة البيانات
3. إعدادات ملف `.env`

