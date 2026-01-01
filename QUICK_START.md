# دليل البدء السريع

## الخطوات السريعة لإعداد النظام

### 1. تحديث قاعدة البيانات

قم بتشغيل migration script لإصلاح مشكلة `telegram_id`:

```bash
python migrate_telegram_id.py
```

### 2. تحديث ملف .env

أضف هذه المتغيرات:

```env
# Admin Group for Approvals
ADMIN_GROUP_ID=-1003482966379

# Web Dashboard
WEB_DASHBOARD_EMAIL=admin@dtcjob.com
WEB_DASHBOARD_PASSWORD=admin123
WEB_DASHBOARD_SECRET_KEY=your-secret-key-change-this
WEB_DASHBOARD_PORT=8000
```

### 3. تثبيت المكتبات الجديدة

```bash
pip install fastapi uvicorn jinja2
```

أو:

```bash
pip install -r requirements.txt
```

### 4. تشغيل البوت

```bash
python main.py
```

### 5. تشغيل الويب داش بورد (في terminal منفصل)

```bash
python web_dashboard.py
```

ثم افتح: `http://localhost:8000`

## الميزات الجديدة

✅ **نظام الموافقة**: جميع الطلبات تُرسل للموافقة قبل النشر
✅ **مجموعة المشرفين**: يمكن قبول/رفض الطلبات من Telegram
✅ **الويب داش بورد**: لوحة تحكم كاملة لإدارة البوت

## ملاحظات

- تأكد من أن البوت عضو في `ADMIN_GROUP_ID` وله صلاحيات إرسال الرسائل
- غير كلمة المرور في الإنتاج
- الويب داش بورد يعمل على المنفذ 8000 افتراضياً

