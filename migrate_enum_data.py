"""
Data Migration Script - Fix Enum Case Mismatch

This script updates all uppercase enum values in the database to lowercase
to match the PostgreSQL enum definitions.
"""
import asyncio
from sqlalchemy import text
from database.base import engine


async def migrate_data():
    """Migrate uppercase enum values to lowercase."""
    
    async with engine.begin() as conn:
        print("🔄 Starting data migration...")
        
        # Update services table - servicestatus enum
        print("\n📝 Updating services table...")
        
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
                print(f"   ⚠️  Could not update '{upper}': {e}")
        
        print(f"   Total updated in services: {total_updated} rows")
        
        # Update service_requests table - requeststatus enum
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
                print(f"   ⚠️  Could not update '{upper}': {e}")
        
        print(f"   Total updated in service_requests: {total_updated} rows")
        
        # Update contact_requests table - contactrequeststatus enum
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
                print(f"   ⚠️  Could not update '{upper}': {e}")
        
        print(f"   Total updated in contact_requests: {total_updated} rows")
        
        print("\n✅ Data migration completed successfully!")
        
        # Verify the changes
        print("\n🔍 Verifying changes...")
        try:
            result = await conn.execute(text("""
                SELECT DISTINCT status FROM services
            """))
            services_statuses = [row[0] for row in result]
            print(f"   Services statuses: {services_statuses}")
        except Exception as e:
            print(f"   Could not verify services: {e}")
        
        try:
            result = await conn.execute(text("""
                SELECT DISTINCT status FROM service_requests
            """))
            requests_statuses = [row[0] for row in result]
            print(f"   Service requests statuses: {requests_statuses}")
        except Exception as e:
            print(f"   Could not verify service_requests: {e}")
        
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
