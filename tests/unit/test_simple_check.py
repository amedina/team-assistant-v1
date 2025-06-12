#!/usr/bin/env python3
import asyncio
from app.data_ingestion.managers.database_manager import DatabaseManager
from app.config.configuration import SystemConfig

async def check_drive_content():
    """Check what content was actually ingested from the Drive file."""
    
    # Initialize database manager properly
    config = SystemConfig.from_yaml('config/data_sources_config.yaml')
    db_manager = DatabaseManager(config.pipeline_config.database)
    await db_manager.initialize()
    
    # Query for recent drive_file chunks using correct table name
    query = '''
    SELECT chunk_uuid, source_type, source_identifier, chunk_text_summary, 
           ingestion_timestamp, chunk_metadata
    FROM document_chunks 
    WHERE source_type = 'drive_file' 
    ORDER BY ingestion_timestamp DESC 
    LIMIT 3
    '''
    
    async with db_manager.get_connection() as conn:
        rows = await conn.fetch(query)
    
    print('Recent Drive File Chunks:')
    print('=' * 80)
    
    if not rows:
        print('❌ NO DRIVE FILE CHUNKS FOUND!')
        print('This means either:')
        print('  1. Drive file was not ingested successfully')
        print('  2. Drive file had permission issues')
        print('  3. Content was stored under different source_type')
        print()
        
        # Check if there are any recent chunks at all
        recent_query = '''
        SELECT source_type, source_identifier, ingestion_timestamp
        FROM document_chunks 
        ORDER BY ingestion_timestamp DESC 
        LIMIT 5
        '''
        recent_rows = await conn.fetch(recent_query)
        
        print('Recent chunks of ANY type:')
        for row in recent_rows:
            print(f'  {row[0]} - {row[1][:50]}... at {row[2]}')
    else:
        for row in rows:
            print(f'UUID: {row[0]}')
            print(f'Source: {row[1]} - {row[2]}')
            content = row[3][:300] if row[3] else 'No content'
            print(f'Content: {content}...')
            print(f'Ingested: {row[4]}')
            print(f'Metadata: {row[5]}')
            
            # Check for expected keywords
            if row[3]:
                content_lower = row[3].lower()
                expected_keywords = ["devrel", "guidance", "documentation", "assistance", "development"]
                found_keywords = [kw for kw in expected_keywords if kw in content_lower]
                missing_keywords = [kw for kw in expected_keywords if kw not in content_lower]
                
                print(f'🔍 Expected keywords: {expected_keywords}')
                print(f'✅ Found keywords: {found_keywords}')
                print(f'❌ Missing keywords: {missing_keywords}')
            
            print('-' * 40)
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_drive_content()) 