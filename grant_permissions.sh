#!/bin/bash
# Script to grant database permissions
# Usage: ./grant_permissions.sh [postgres_password]

DB_NAME="dtc"
DB_USER="fayez"
POSTGRES_PASSWORD="${1:-}"

echo "🔐 إعطاء الصلاحيات للمستخدم: $DB_USER"
echo ""

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "⚠️  سيتم استخدام sudo للاتصال كـ postgres"
    echo ""
    
    # Try using sudo
    sudo -u postgres psql -d "$DB_NAME" <<EOF
-- منح الصلاحيات الأساسية
GRANT USAGE ON SCHEMA public TO $DB_USER;
GRANT CREATE ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- منح الصلاحيات على الجداول الموجودة
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

-- منح الصلاحيات على الكائنات المستقبلية
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

\echo '✅ تم منح الصلاحيات بنجاح!'
EOF
else
    echo "📝 استخدام كلمة المرور المقدمة"
    echo ""
    
    # Use password via PGPASSWORD
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U postgres -d "$DB_NAME" <<EOF
-- منح الصلاحيات الأساسية
GRANT USAGE ON SCHEMA public TO $DB_USER;
GRANT CREATE ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- منح الصلاحيات على الجداول الموجودة
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

-- منح الصلاحيات على الكائنات المستقبلية
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

\echo '✅ تم منح الصلاحيات بنجاح!'
EOF
fi

echo ""
echo "🎉 اكتمل!"

