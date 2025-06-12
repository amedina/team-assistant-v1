#!/usr/bin/env python3
import asyncio
from data_ingestion.managers.database_manager import DatabaseManager
from app.config.configuration import SystemConfig

async def check_recent_drive_files():
    config = SystemConfig.from_yaml('config/data_sources_config.yaml')
    db_manager = DatabaseManager(config.pipeline_config)
    await db_manager.initialize()
    
    # Query for recent drive_file chunks
    query = '''
    SELECT chunk_uuid, source_type, source_identifier, chunk_text_summary, ingestion_timestamp, chunk_metadata
    FROM chunks 
    WHERE source_type = 'drive_file' 
    ORDER BY ingestion_timestamp DESC 
    LIMIT 5
    '''
    
    results = await db_manager.execute_query(query)
    
    print('Recent Drive File Chunks:')
    print('=' * 80)
    for row in results:
        print(f'UUID: {row[0]}')
        print(f'Source: {row[1]} - {row[2]}') 
        print(f'Content: {row[3][:300]}...' if row[3] else 'No content')
        print(f'Ingested: {row[4]}')
        print(f'Metadata: {row[5]}')
        print('-' * 40)
    
    await db_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(check_recent_drive_files()) 