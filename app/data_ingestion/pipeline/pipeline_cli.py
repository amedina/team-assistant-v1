#!/usr/bin/env python3
"""
DevRel Assistant Data Ingestion Pipeline CLI

A unified command-line interface for managing and executing data ingestion pipelines.
"""

import asyncio
import argparse
import json
import sys
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import asdict

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.config.configuration import get_config_manager
from app.data_ingestion.pipeline.pipeline_manager import PipelineManager, SyncMode, PipelineStats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineCLI:
    """Command-line interface for the data ingestion pipeline."""
    
    def __init__(self):
        self.pipeline_manager: Optional[PipelineManager] = None
    
    def _init_pipeline_manager(self, config_file: str = "app/config/data_sources_config.yaml") -> None:
        """Initialize the pipeline manager."""
        try:
            # Set the config file path if it's not the default
            config_manager = get_config_manager(config_file)
            config = config_manager.config

            self.pipeline_manager = PipelineManager(config)
            logger.info("Pipeline manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline manager: {e}")
            sys.exit(1)
    
    async def run_pipeline(self, args) -> None:
        """Run the data ingestion pipeline."""
        self._init_pipeline_manager(args.config)
        
        try:
            # Initialize the pipeline
            await self.pipeline_manager.initialize()
            
            # Determine execution mode
            mode_mapping = {
                "dev": SyncMode.SMART_SYNC,
                "smart": SyncMode.SMART_SYNC,
                "incremental": SyncMode.INCREMENTAL_SYNC,
                "full": SyncMode.FULL_SYNC,
                "vector": SyncMode.FULL_SYNC  # For compatibility
            }
            
            sync_mode = mode_mapping.get(args.mode, SyncMode.SMART_SYNC)
            source_filter = args.source_filter.split(",") if args.source_filter else None
            
            logger.info(f"Starting pipeline in {args.mode} mode (sync_mode: {sync_mode.value})")
            if source_filter:
                logger.info(f"Filtering sources: {source_filter}")
            
            # Run the pipeline
            result = await self.pipeline_manager.run_pipeline(
                source_ids=source_filter,
                sync_mode=sync_mode,
                limit=getattr(args, 'limit', None)
            )
            
            # Display results
            self._display_pipeline_result(result, args.output_file)
            
            # Exit with appropriate code based on comprehensive success criteria
            # Determine exit code based on results
            has_storage_errors = len(result.errors) > 0  # Storage/processing system errors
            has_successful_chunks = result.successful_chunks > 0
            has_failed_documents = result.failed_documents > 0
            chunks_fully_stored = result.successful_chunks == result.total_chunks
            
            if has_successful_chunks and not has_storage_errors and chunks_fully_stored:
                # Success: all processable data stored successfully
                if has_failed_documents:
                    logger.info(f"Pipeline completed successfully with notes: {result.failed_documents} documents failed processing (likely no content/parse errors)")
                else:
                    logger.info("Pipeline completed successfully - all data processed and stored")
                sys.exit(0)
            elif has_successful_chunks and has_storage_errors:
                # Partial success: some data stored but with storage system errors
                logger.error(f"Pipeline completed with storage errors: {len(result.errors)} storage errors, {result.failed_documents} failed documents")
                sys.exit(1)
            else:
                # Complete failure: no data stored successfully
                logger.error("Pipeline failed completely - no data was successfully processed")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            sys.exit(1)
        finally:
            if self.pipeline_manager:
                await self.pipeline_manager.cleanup()
    
    async def check_status(self, args) -> None:
        """Check the status of pipeline components."""
        self._init_pipeline_manager(args.config)
        
        try:
            # Initialize the pipeline
            await self.pipeline_manager.initialize()
            
            logger.info("Checking pipeline component health...")
            health_result = await self.pipeline_manager.health_check()
            
            # Display health status
            print("\n" + "="*60)
            print("PIPELINE HEALTH STATUS")
            print("="*60)
            
            status_color = "✅" if health_result.overall_status else "❌"
            print(f"Overall Status: {status_color} {'HEALTHY' if health_result.overall_status else 'UNHEALTHY'}")
            print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            print("\nComponent Status:")
            print("-" * 40)
            
            # Vector Search
            vs_color = "✅" if health_result.vector_store_healthy else "❌"
            print(f"Vector Search: {vs_color} {'healthy' if health_result.vector_store_healthy else 'unhealthy'}")
            
            # Database
            db_color = "✅" if health_result.database_healthy else "❌"
            print(f"Database: {db_color} {'healthy' if health_result.database_healthy else 'unhealthy'}")
            
            # Knowledge Graph
            kg_color = "✅" if health_result.knowledge_graph_healthy else "❌"
            print(f"Knowledge Graph: {kg_color} {'healthy' if health_result.knowledge_graph_healthy else 'unhealthy'}")
            
            # Show issues if any
            if health_result.issues:
                print(f"\nIssues ({len(health_result.issues)}):")
                for issue in health_result.issues:
                    print(f"  ❌ {issue}")
            
            if args.output_file:
                health_data = {
                    "overall_status": health_result.overall_status,
                    "vector_store_healthy": health_result.vector_store_healthy,
                    "database_healthy": health_result.database_healthy,
                    "knowledge_graph_healthy": health_result.knowledge_graph_healthy,
                    "issues": health_result.issues,
                    "checked_at": datetime.now().isoformat()
                }
                self._save_to_file(health_data, args.output_file)
                print(f"\nDetailed status saved to: {args.output_file}")
            
            # Exit with appropriate code
            sys.exit(0 if health_result.overall_status else 1)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            sys.exit(1)
        finally:
            if self.pipeline_manager:
                await self.pipeline_manager.cleanup()
    
    async def get_statistics(self, args) -> None:
        """Get pipeline and data statistics."""
        self._init_pipeline_manager(args.config)
        
        try:
            # Initialize the pipeline
            await self.pipeline_manager.initialize()
            
            logger.info("Gathering pipeline statistics...")
            stats = await self.pipeline_manager.get_pipeline_stats()
            
            # Display statistics
            print("\n" + "="*60)
            print("PIPELINE STATISTICS")
            print("="*60)
            
            # Configuration stats
            config_stats = stats.get("configuration", {})
            print(f"Enabled Sources: {stats.get('enabled_sources', 0)}")
            print(f"Chunk Size: {config_stats.get('chunk_size', 'unknown')}")
            print(f"Chunk Overlap: {config_stats.get('chunk_overlap', 'unknown')}")
            print(f"Max Concurrent Jobs: {config_stats.get('max_concurrent_jobs', 'unknown')}")
            print(f"Knowledge Graph: {'Enabled' if config_stats.get('enable_knowledge_graph') else 'Disabled'}")
            
            # Component stats
            components = stats.get("components", {})
            print(f"\nComponents Active:")
            print(f"  Vector Store: {'✅' if components.get('vector_store') else '❌'}")
            print(f"  Database: {'✅' if components.get('database') else '❌'}")
            print(f"  Knowledge Graph: {'✅' if components.get('knowledge_graph') else '❌'}")
            print(f"  Text Processor: {'✅' if components.get('text_processor') else '❌'}")
            
            # Database stats
            db_stats = stats.get("database_stats", {})
            if db_stats:
                print(f"\nDatabase Statistics:")
                print(f"  Total Chunks: {db_stats.get('total_chunks', 0)}")
                
                by_source_type = db_stats.get('by_source_type', {})
                if by_source_type:
                    print(f"  Chunks by Source Type:")
                    for source_type, count in by_source_type.items():
                        print(f"    {source_type}: {count}")
                
                recent_activity = db_stats.get('recent_activity', [])
                if recent_activity:
                    print(f"  Recent Activity (last 7 days):")
                    for activity in recent_activity[:5]:  # Show last 5 days
                        date = activity.get('date', 'unknown')
                        count = activity.get('count', 0)
                        print(f"    {date}: {count} chunks")
            
            # Knowledge Graph stats
            kg_stats = stats.get("knowledge_graph_stats", {})
            if kg_stats:
                print(f"\nKnowledge Graph Statistics:")
                print(f"  Total Entities: {kg_stats.get('total_entities', 0)}")
                print(f"  Total Relationships: {kg_stats.get('total_relationships', 0)}")
                
                entity_types = kg_stats.get('entity_types', {})
                if entity_types:
                    print(f"  Entity Types:")
                    for entity_type, count in list(entity_types.items())[:5]:  # Show top 5
                        print(f"    {entity_type}: {count}")
            
            # Vector Search stats
            vs_stats = stats.get("vector_store_stats", {})
            if vs_stats:
                print(f"\nVector Search Statistics:")
                print(f"  Index ID: {vs_stats.get('index_id', 'unknown')}")
                print(f"  Endpoint ID: {vs_stats.get('endpoint_id', 'unknown')}")
                if vs_stats.get('dimensions'):
                    print(f"  Dimensions: {vs_stats.get('dimensions')}")
            
            print(f"\nPipeline Status: {stats.get('pipeline_status', 'unknown')}")
            print(f"Initialized: {'✅' if stats.get('initialized') else '❌'}")
            
            if args.output_file:
                self._save_to_file(stats, args.output_file)
                print(f"\nDetailed statistics saved to: {args.output_file}")
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            sys.exit(1)
        finally:
            if self.pipeline_manager:
                await self.pipeline_manager.cleanup()
    
    async def validate_setup(self, args) -> None:
        """Validate system setup and configuration."""
        self._init_pipeline_manager(args.config)
        
        try:
            # Initialize the pipeline
            await self.pipeline_manager.initialize()
            
            logger.info("Validating system setup...")
            
            # Use health check for validation
            health_result = await self.pipeline_manager.health_check()
            
            print("\n" + "="*60)
            print("SYSTEM SETUP VALIDATION")
            print("="*60)
            
            # Overall status
            status_icon = "✅" if health_result.overall_status else "❌"
            print(f"Overall Status: {status_icon} {'VALID' if health_result.overall_status else 'INVALID'}")
            
            # Individual component checks
            print("\nComponent Validation:")
            print("-" * 40)
            
            vs_icon = "✅" if health_result.vector_store_healthy else "❌"
            print(f"{vs_icon} Vector Store Connection: {'PASS' if health_result.vector_store_healthy else 'FAIL'}")
            
            db_icon = "✅" if health_result.database_healthy else "❌"
            print(f"{db_icon} Database Connection: {'PASS' if health_result.database_healthy else 'FAIL'}")
            
            kg_icon = "✅" if health_result.knowledge_graph_healthy else "❌"
            print(f"{kg_icon} Knowledge Graph Connection: {'PASS' if health_result.knowledge_graph_healthy else 'FAIL'}")
            
            # Configuration validation
            config_manager = get_config_manager()
            config_issues = config_manager.validate_config()
            
            config_icon = "✅" if not config_issues else "❌"
            print(f"{config_icon} Configuration: {'VALID' if not config_issues else 'INVALID'}")
            
            # Show configuration issues
            if config_issues:
                print(f"\nConfiguration Issues ({len(config_issues)}):")
                for issue in config_issues:
                    print(f"  ❌ {issue}")
            
            # Show system issues
            if health_result.issues:
                print(f"\nSystem Issues ({len(health_result.issues)}):")
                for issue in health_result.issues:
                    print(f"  ❌ {issue}")
            
            if args.output_file:
                validation_data = {
                    "overall_status": health_result.overall_status and not config_issues,
                    "vector_store_healthy": health_result.vector_store_healthy,
                    "database_healthy": health_result.database_healthy,
                    "knowledge_graph_healthy": health_result.knowledge_graph_healthy,
                    "configuration_valid": not config_issues,
                    "system_issues": health_result.issues,
                    "config_issues": config_issues,
                    "validated_at": datetime.now().isoformat()
                }
                self._save_to_file(validation_data, args.output_file)
                print(f"\nDetailed validation results saved to: {args.output_file}")
            
            # Exit with appropriate code
            overall_valid = health_result.overall_status and not config_issues
            sys.exit(0 if overall_valid else 1)
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            sys.exit(1)
        finally:
            if self.pipeline_manager:
                await self.pipeline_manager.cleanup()
    
    async def test_connections(self, args) -> None:
        """Test connectivity to all components."""
        self._init_pipeline_manager(args.config)
        
        try:
            # Initialize the pipeline
            await self.pipeline_manager.initialize()
            
            logger.info("Testing component connectivity...")
            
            # Run health check which tests all connections
            health_result = await self.pipeline_manager.health_check()
            
            print("\n" + "="*60)
            print("CONNECTIVITY TEST RESULTS")
            print("="*60)
            
            # Test Vector Search
            vs_icon = "✅" if health_result.vector_store_healthy else "❌"
            print(f"Vector Store:")
            print(f"  {vs_icon} Connection: {'PASS' if health_result.vector_store_healthy else 'FAIL'}")
            
            # Test Database
            db_icon = "✅" if health_result.database_healthy else "❌"
            print(f"\nDatabase:")
            print(f"  {db_icon} Connection: {'PASS' if health_result.database_healthy else 'FAIL'}")
            
            # Test Knowledge Graph
            kg_icon = "✅" if health_result.knowledge_graph_healthy else "❌"
            print(f"\nKnowledge Graph:")
            print(f"  {kg_icon} Neo4j Connection: {'PASS' if health_result.knowledge_graph_healthy else 'FAIL'}")
            
            # Test Configuration
            config_manager = get_config_manager()
            enabled_sources = config_manager.config.get_enabled_sources()
            print(f"\nData Sources Configuration:")
            print(f"  Total Enabled Sources: {len(enabled_sources)}")
            for source in enabled_sources:
                print(f"    ✅ {source.source_id} ({source.source_type})")
            
            # Overall result
            print(f"\nOverall Connectivity: {'✅ PASS' if health_result.overall_status else '❌ FAIL'}")
            
            # Show issues if any
            if health_result.issues:
                print(f"\nConnection Issues:")
                for issue in health_result.issues:
                    print(f"  ❌ {issue}")
            
            sys.exit(0 if health_result.overall_status else 1)
            
        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            sys.exit(1)
        finally:
            if self.pipeline_manager:
                await self.pipeline_manager.cleanup()
    
    def _display_pipeline_result(self, result: PipelineStats, output_file: Optional[str] = None) -> None:
        """Display pipeline execution results."""
        print("\n" + "="*60)
        print("PIPELINE EXECUTION RESULTS")
        print("="*60)
        
        # Basic info
        print(f"Start Time: {result.start_time}")
        print(f"End Time: {result.end_time}")
        print(f"Duration: {result.duration}")
        
        # Processing stats
        print(f"\nProcessing Summary:")
        print(f"  Total Documents: {result.total_documents}")
        print(f"  Successful: {result.successful_documents}")
        print(f"  Failed: {result.failed_documents}")
        print(f"  Total Chunks: {result.total_chunks}")
        print(f"  Total Entities: {result.total_entities}")
        print(f"  Total Relationships: {result.total_relationships}")
        
        # Source details
        if result.sources_processed:
            print(f"\nSources Processed ({len(result.sources_processed)}):")
            for source_id in result.sources_processed:
                print(f"  ✅ {source_id}")
        
        # Show processing times
        if result.processing_times:
            print(f"\nProcessing Times:")
            for stage, time_taken in result.processing_times.items():
                print(f"  {stage}: {time_taken:.2f}s")
        
        # Errors
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                print(f"  ❌ {error}")
        
        # Overall status based on comprehensive criteria
        has_storage_errors = len(result.errors) > 0  # Storage/processing system errors
        has_successful_chunks = result.successful_chunks > 0
        has_failed_documents = result.failed_documents > 0
        chunks_fully_stored = result.successful_chunks == result.total_chunks
        
        if has_successful_chunks and not has_storage_errors and chunks_fully_stored:
            if has_failed_documents:
                print(f"\n✅ Pipeline completed successfully with notes!")
                print(f"   • {result.successful_chunks}/{result.total_chunks} chunks stored across ALL storage systems")
                print(f"   • {result.failed_documents} documents failed processing (likely no content/parse errors)")
                print(f"   • All processable documents were successfully stored")
            else:
                print(f"\n✅ Pipeline completed successfully!")
                print(f"   • {result.successful_chunks}/{result.total_chunks} chunks stored across ALL storage systems")
        elif has_successful_chunks and has_storage_errors:
            print(f"\n⚠️  Pipeline completed with STORAGE ERRORS!")
            print(f"   • {result.successful_chunks}/{result.total_chunks} chunks fully stored (across ALL systems)")
            print(f"   • {len(result.errors)} storage/processing errors occurred")
            if has_failed_documents:
                print(f"   • {result.failed_documents} documents failed processing")
            print(f"   • Some chunks may be partially stored (in database but not vector store)")
        else:
            print(f"\n❌ Pipeline FAILED completely!")
            print(f"   • {result.successful_chunks}/{result.total_chunks} chunks fully stored")
            print(f"   • {len(result.errors)} storage/processing errors occurred")
            if has_failed_documents:
                print(f"   • {result.failed_documents} documents failed processing")
            print(f"   • Pipeline unable to store data across required storage systems")
        
        # Save detailed results if requested
        if output_file:
            result_dict = asdict(result)
            # Convert datetime objects to strings for JSON serialization
            result_dict["start_time"] = result.start_time.isoformat()
            result_dict["end_time"] = result.end_time.isoformat()
            
            self._save_to_file(result_dict, output_file)
            print(f"\nDetailed results saved to: {output_file}")
    
    def _save_to_file(self, data: Dict[str, Any], filename: str) -> None:
        """Save data to a JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save to file {filename}: {e}")

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="DevRel Assistant Data Ingestion Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate system setup (recommended first step)
  python pipeline_cli.py validate
  
  # Run smart sync pipeline (default - processes only changed content)
  python pipeline_cli.py run
  
  # Run in quiet mode (only warnings, errors, and summary)
  python pipeline_cli.py --quiet run
  
  # Run full sync pipeline (processes all content)
  python pipeline_cli.py run --mode full
  
  # Run with document limit for testing
  python pipeline_cli.py --quiet run --limit 5
  
  # Run incremental sync for specific sources
  python pipeline_cli.py run --mode incremental --source-filter "ps-analysis-tool,devrel-docs"
  
  # Run with verbose logging (shows all INFO messages)
  python pipeline_cli.py --verbose run
  
  # Check system health
  python pipeline_cli.py status
  
  # Test connectivity
  python pipeline_cli.py test
  
  # Get statistics
  python pipeline_cli.py stats --output-file stats.json
        """
    )
    
    # Global options
    parser.add_argument(
        "--config", 
        default="app/config/data_sources_config.yaml",
        help="Path to configuration file (default: config/data_sources_config.yaml)"
    )
    parser.add_argument(
        "--output-file", 
        help="Save detailed output to JSON file"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Enable verbose logging (shows all INFO messages)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true", 
        help="Quiet mode - only show warnings, errors, and final summary"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the data ingestion pipeline")
    run_parser.add_argument(
        "--mode", 
        choices=["smart", "incremental", "full"],
        default="smart",
        help="Pipeline execution mode: smart (changed content only), incremental (new content only), full (all content) (default: smart)"
    )
    run_parser.add_argument(
        "--source-filter",
        help="Comma-separated list of source IDs to process"
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of documents to process (useful for testing)"
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check pipeline component health")
    
    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Get pipeline statistics")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test component connectivity")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate system setup and configuration")
    
    return parser

async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging level based on flags
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("data_ingestion").setLevel(logging.DEBUG)
    elif args.quiet:
        # Quiet mode: only show warnings and errors
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger("data_ingestion").setLevel(logging.WARNING)
    else:
        # Default mode: show info and above, but reduce noise from data_ingestion modules
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger("data_ingestion").setLevel(logging.WARNING)
    
    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = PipelineCLI()
    
    try:
        # Execute command
        if args.command == "run":
            await cli.run_pipeline(args)
        elif args.command == "status":
            await cli.check_status(args)
        elif args.command == "stats":
            await cli.get_statistics(args)
        elif args.command == "test":
            await cli.test_connections(args)
        elif args.command == "validate":
            await cli.validate_setup(args)
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
