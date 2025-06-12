#!/usr/bin/env python3
"""
Diagnostic script to trace UUID generation during text processing.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data_ingestion.processors.text_processor import TextProcessor

async def diagnose_uuid_generation():
    """Diagnose UUID generation during text processing."""
    print("🔍 DIAGNOSING UUID GENERATION IN TEXT PROCESSING")
    print("="*60)
    
    # Create a sample document with substantial content
    sample_document = {
        "document_id": "test-doc-001",
        "source_type": "github_repo", 
        "source_identifier": "GoogleChromeLabs/ps-analysis-tool",
        "text": """# Privacy Sandbox Analysis Tool

This repository contains the Privacy Sandbox Analysis Tool, a comprehensive testing framework for Chrome privacy features.

## Overview

The Privacy Sandbox is Google's initiative to create web technologies that protect user privacy while still enabling digital businesses to thrive. This tool helps developers analyze and test various privacy-preserving APIs.

## Features

- Privacy Budget Analysis
- Topics API Testing
- FLEDGE API Integration
- Attribution Reporting Validation
- Trust Tokens Implementation
- Comprehensive reporting and analytics

## Installation

To install the Privacy Sandbox Analysis Tool:

1. Clone this repository
2. Run npm install
3. Configure your environment variables
4. Execute the test suite

## Usage

The tool provides several testing modes for different privacy APIs and scenarios. Each test generates detailed reports about privacy budget consumption and API effectiveness.

## Contributing

We welcome contributions to improve the Privacy Sandbox Analysis Tool. Please read our contributing guidelines before submitting pull requests.""",
        "metadata": {
            "source_type": "github_repo",
            "source_identifier": "GoogleChromeLabs/ps-analysis-tool",
            "file_path": "README.md",
            "last_modified": datetime.now(),
            "content_type": "markdown"
        }
    }
    
    print(f"\n📋 Processing sample document:")
    print(f"   Document ID: {sample_document['document_id']}")
    print(f"   Source Type: {sample_document['source_type']}")
    print(f"   Source ID: {sample_document['source_identifier']}")
    
    # Initialize text processor
    text_processor = TextProcessor(
        chunk_size=500,
        chunk_overlap=50,
        enable_entity_extraction=True
    )
    
    # Process the document
    print(f"\n🔄 Processing document through TextProcessor...")
    processed_doc = await text_processor.process_document(sample_document)
    
    print(f"\n📊 Processing Results:")
    print(f"   Chunks created: {len(processed_doc.chunks)}")
    
    # Examine each chunk's UUID
    for i, chunk in enumerate(processed_doc.chunks):
        print(f"\n   Chunk {i+1}:")
        print(f"      UUID: {chunk.chunk_uuid}")
        print(f"      UUID Type: {type(chunk.chunk_uuid)}")
        print(f"      Text Preview: {chunk.text[:50]}...")
        
        # Check if it's a valid UUID format
        try:
            from uuid import UUID
            UUID(str(chunk.chunk_uuid))
            print(f"      ✅ Valid UUID format")
        except ValueError:
            print(f"      ❌ INVALID UUID format - this is the problem!")
        
        # Check metadata
        if hasattr(chunk, 'metadata'):
            print(f"      Metadata keys: {list(chunk.metadata.keys())}")
            if 'source_identifier' in chunk.metadata:
                print(f"      Source in metadata: {chunk.metadata['source_identifier']}")

if __name__ == "__main__":
    asyncio.run(diagnose_uuid_generation()) 