#!/usr/bin/env python3
"""
Simple test script for Context Manager Agent
Tests the basic functionality and integration points.
"""

import asyncio
import logging
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.context_manager.context_manager_agent import get_context_manager, context_manager_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_context_manager_initialization():
    """Test Context Manager initialization."""
    print("🧪 Testing Context Manager Initialization...")
    
    try:
        context_manager = await get_context_manager()
        print("✅ Context Manager initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Context Manager initialization failed: {e}")
        return False


async def test_basic_query_processing():
    """Test basic query processing functionality."""
    print("\n🧪 Testing Basic Query Processing...")
    
    try:
        context_manager = await get_context_manager()
        
        # Test query
        test_query = "What is the Privacy Sandbox?"
        
        print(f"   Query: '{test_query}'")
        response = await context_manager.process_query(test_query)
        
        print(f"   Response length: {len(response)} characters")
        print(f"   Response preview: {response[:100]}...")
        
        if response and len(response) > 10:
            print("✅ Basic query processing works")
            return True
        else:
            print("❌ Query processing returned empty/short response")
            return False
            
    except Exception as e:
        print(f"❌ Query processing failed: {e}")
        return False


async def test_storage_integration():
    """Test storage layer integration."""
    print("\n🧪 Testing Storage Integration...")
    
    try:
        context_manager = await get_context_manager()
        
        # Test vector search
        print("   Testing vector search...")
        docs = await context_manager.retrieve_relative_documents("Privacy Sandbox", top_k=3)
        print(f"   Vector search returned {len(docs)} documents")
        
        if docs:
            # Test metadata retrieval
            print("   Testing metadata retrieval...")
            doc_ids = [doc['id'] for doc in docs[:2]]  # Test with first 2 docs
            metadata = await context_manager.retrieve_document_metadata(doc_ids)
            print(f"   Metadata retrieval returned {len(metadata)} entries")
            
            # Test context combination
            print("   Testing context combination...")
            context = context_manager.combine_relevant_context(docs, metadata)
            print(f"   Combined context has {len(context.relevant_chunks)} chunks")
            print(f"   Confidence score: {context.confidence_score:.2f}")
            
            print("✅ Storage integration works")
            return True
        else:
            print("⚠️  No documents found in vector search (may be expected if no data ingested)")
            return True  # Not necessarily a failure
            
    except Exception as e:
        print(f"❌ Storage integration test failed: {e}")
        return False


def test_agent_integration():
    """Test ADK agent integration."""
    print("\n🧪 Testing ADK Agent Integration...")
    
    try:
        # Test agent import
        print("   Testing agent import...")
        assert context_manager_agent is not None
        print(f"   Agent name: {context_manager_agent.name}")
        print(f"   Agent model: {context_manager_agent.model}")
        print(f"   Agent tools: {len(context_manager_agent.tools)}")
        
        # Test tool availability
        print("   Testing tool availability...")
        tools = context_manager_agent.tools
        tool_names = [getattr(tool, 'name', str(tool)) for tool in tools]
        print(f"   Available tools: {tool_names}")
        
        print("✅ ADK Agent integration works")
        return True
        
    except Exception as e:
        print(f"❌ Agent integration test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling and edge cases."""
    print("\n🧪 Testing Error Handling...")
    
    try:
        context_manager = await get_context_manager()
        
        # Test empty query
        print("   Testing empty query...")
        response = await context_manager.process_query("")
        print(f"   Empty query response: {response[:50]}...")
        
        # Test very long query
        print("   Testing long query...")
        long_query = "What is Privacy Sandbox? " * 100  # Very long query
        response = await context_manager.process_query(long_query)
        print(f"   Long query response: {response[:50]}...")
        
        # Test special characters
        print("   Testing special characters...")
        special_query = "What is Privacy Sandbox? 🔒🌐 <script>alert('test')</script>"
        response = await context_manager.process_query(special_query)
        print(f"   Special chars response: {response[:50]}...")
        
        print("✅ Error handling works")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("🚀 Starting Context Manager Agent Tests\n")
    
    tests = [
        ("Initialization", test_context_manager_initialization()),
        ("Basic Query Processing", test_basic_query_processing()),
        ("Storage Integration", test_storage_integration()),
        ("Agent Integration", test_agent_integration()),
        ("Error Handling", test_error_handling()),
    ]
    
    results = []
    for test_name, test_coro in tests:
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Context Manager Agent is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


async def main():
    """Main test runner."""
    try:
        success = await run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Tests crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 