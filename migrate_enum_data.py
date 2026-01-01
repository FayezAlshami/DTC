"""
Data Migration Script - Fix Enum Case Mismatch

This script updates all uppercase enum values in the database to lowercase
to match the PostgreSQL enum definitions.
"""
import asyncio
from sqlalchemy import text
from database.base import engine


async def check_table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = await conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = :table_name
        );
    """), {"table_name": table_name})
    return result.scalar()


async def migrate_data():
    """Migrate uppercase enum values to lowercase."""
    
    async with engine.begin() as conn:
        print("🔄 Starting data migration...")
        
        # Check if tables exist
        services_exists = await check_table_exists(conn, "services")
        requests_exists = await check_table_exists(conn, "service_requests")
        contacts_exists = await check_table_exists(conn, "contact_requests")
        
        if not services_exists and not requests_exists and not contacts_exists:
            print("\n⚠️  الجداول غير موجودة في قاعدة البيانات!")
            print("يرجى تشغيل setup_database.py أولاً لإنشاء الجداول:")
            print("  python setup_database.py")
            return
        
        # Map of uppercase to lowercase
        status_mappings = {
            'DRAFT': 'draft',
            'PENDING': 'pending',
            'PUBLISHED': 'published',
            'REMOVED': 'removed',
            'COMPLETED': 'completed',
            'CONTACT_ACCEPTED': 'contact_accepted',
            'EXPIRED': 'expired',
            'REJECTED': 'rejected'
        }
        
        # Update services table - servicestatus enum
        if services_exists:
            print("\n📝 Updating services table...")
            total_updated = 0
            for upper, lower in status_mappings.items():
                try:
                    result = await conn.execute(text(f"""
                        UPDATE services 
                        SET status = '{lower}'::servicestatus
                        WHERE status::text = '{upper}'
                    """))
                    if result.rowcount > 0:
                        print(f"   ✅ Updated {result.rowcount} rows from '{upper}' to '{lower}'")
                        total_updated += result.rowcount
                except Exception as e:
                    error_msg = str(e)
                    if "does not exist" in error_msg or "UndefinedTableError" in error_msg:
                        print(f"   ⚠️  Table 'services' does not exist. Skipping...")
                        break
                    else:
                        print(f"   ⚠️  Could not update '{upper}': {error_msg}")
            
            print(f"   Total updated in services: {total_updated} rows")
        else:
            print("\n⚠️  Table 'services' does not exist. Skipping...")
        
        # Update service_requests table - requeststatus enum
        if requests_exists:
            print("\n📝 Updating service_requests table...")
            total_updated = 0
            for upper, lower in status_mappings.items():
                try:
                    result = await conn.execute(text(f"""
                        UPDATE service_requests 
                        SET status = '{lower}'::requeststatus
                        WHERE status::text = '{upper}'
                    """))
                    if result.rowcount > 0:
                        print(f"   ✅ Updated {result.rowcount} rows from '{upper}' to '{lower}'")
                        total_updated += result.rowcount
                except Exception as e:
                    error_msg = str(e)
                    if "does not exist" in error_msg or "UndefinedTableError" in error_msg:
                        print(f"   ⚠️  Table 'service_requests' does not exist. Skipping...")
                        break
                    elif "InFailedSQLTransactionError" in error_msg:
                        # Transaction already failed, skip remaining
                        break
                    else:
                        print(f"   ⚠️  Could not update '{upper}': {error_msg}")
            
            print(f"   Total updated in service_requests: {total_updated} rows")
        else:
            print("\n⚠️  Table 'service_requests' does not exist. Skipping...")
        
        # Update contact_requests table - contactrequeststatus enum
        if contacts_exists:
            print("\n📝 Updating contact_requests table...")
            contact_status_mappings = {
                'PENDING': 'pending',
                'ACCEPTED': 'accepted',
                'REJECTED': 'rejected'
            }
            
            total_updated = 0
            for upper, lower in contact_status_mappings.items():
                try:
                    result = await conn.execute(text(f"""
                        UPDATE contact_requests 
                        SET status = '{lower}'::contactrequeststatus
                        WHERE status::text = '{upper}'
                    """))
                    if result.rowcount > 0:
                        print(f"   ✅ Updated {result.rowcount} rows from '{upper}' to '{lower}'")
                        total_updated += result.rowcount
                except Exception as e:
                    error_msg = str(e)
                    if "does not exist" in error_msg or "UndefinedTableError" in error_msg:
                        print(f"   ⚠️  Table 'contact_requests' does not exist. Skipping...")
                        break
                    elif "InFailedSQLTransactionError" in error_msg:
                        # Transaction already failed, skip remaining
                        break
                    else:
                        print(f"   ⚠️  Could not update '{upper}': {error_msg}")
            
            print(f"   Total updated in contact_requests: {total_updated} rows")
        else:
            print("\n⚠️  Table 'contact_requests' does not exist. Skipping...")
        
        print("\n✅ Data migration completed successfully!")
        
        # Verify the changes (only if tables exist)
        if services_exists or requests_exists or contacts_exists:
            print("\n🔍 Verifying changes...")
            if services_exists:
                try:
                    result = await conn.execute(text("""
                        SELECT DISTINCT status FROM services
                    """))
                    services_statuses = [row[0] for row in result]
                    print(f"   Services statuses: {services_statuses}")
                except Exception as e:
                    print(f"   Could not verify services: {e}")
            
            if requests_exists:
                try:
                    result = await conn.execute(text("""
                        SELECT DISTINCT status FROM service_requests
                    """))
                    requests_statuses = [row[0] for row in result]
                    print(f"   Service requests statuses: {requests_statuses}")
                except Exception as e:
                    print(f"   Could not verify service_requests: {e}")
            
            if contacts_exists:
                try:
                    result = await conn.execute(text("""
                        SELECT DISTINCT status FROM contact_requests
                    """))
                    contact_statuses = [row[0] for row in result]
                    print(f"   Contact requests statuses: {contact_statuses}")
                except Exception as e:
                    print(f"   Could not verify contact_requests: {e}")


if __name__ == "__main__":
    asyncio.run(migrate_data())
