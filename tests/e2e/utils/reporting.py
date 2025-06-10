"""
Reporting utilities for E2E testing.

This module provides comprehensive test result reporting, metrics collection,
and formatted output for E2E test results.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from ..test_scenarios import TestScenario

logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """Metrics for a single test execution."""
    scenario_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    ingestion_time_ms: Optional[float] = None
    retrieval_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None
    chunks_ingested: int = 0
    chunks_retrieved: int = 0
    error_messages: List[str] = None
    warnings: List[str] = None
    storage_targets_tested: List[str] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
        if self.warnings is None:
            self.warnings = []
        if self.storage_targets_tested is None:
            self.storage_targets_tested = []
    
    @property
    def duration_ms(self) -> float:
        """Calculate test duration in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0
    
    def finish(self, success: bool, error_message: Optional[str] = None):
        """Mark test as finished."""
        self.end_time = datetime.now()
        self.success = success
        self.total_time_ms = self.duration_ms
        
        if error_message:
            self.error_messages.append(error_message)


@dataclass
class E2ETestReport:
    """Comprehensive E2E test execution report."""
    test_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    scenarios_tested: List[str] = None
    test_metrics: Dict[str, TestMetrics] = None
    overall_success: bool = False
    total_scenarios: int = 0
    successful_scenarios: int = 0
    failed_scenarios: int = 0
    skipped_scenarios: int = 0
    configuration_summary: Dict[str, Any] = None
    system_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.scenarios_tested is None:
            self.scenarios_tested = []
        if self.test_metrics is None:
            self.test_metrics = {}
        if self.configuration_summary is None:
            self.configuration_summary = {}
        if self.system_info is None:
            self.system_info = {}
    
    def add_test_metrics(self, metrics: TestMetrics):
        """Add test metrics for a scenario."""
        self.test_metrics[metrics.scenario_id] = metrics
        self.scenarios_tested.append(metrics.scenario_id)
        
        if metrics.success:
            self.successful_scenarios += 1
        else:
            self.failed_scenarios += 1
        
        self.total_scenarios = len(self.test_metrics)
    
    def finalize(self):
        """Finalize the report."""
        self.end_time = datetime.now()
        self.overall_success = (
            self.failed_scenarios == 0 and 
            self.successful_scenarios > 0
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_scenarios == 0:
            return 0.0
        return self.successful_scenarios / self.total_scenarios
    
    @property
    def total_duration_ms(self) -> float:
        """Calculate total test session duration in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0


class E2EReporter:
    """E2E test result reporter."""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("test_results")
        self.output_dir.mkdir(exist_ok=True)
        self.current_report: Optional[E2ETestReport] = None
    
    def start_session(self, test_session_id: str, config_summary: Dict[str, Any]) -> E2ETestReport:
        """Start a new test session."""
        self.current_report = E2ETestReport(
            test_session_id=test_session_id,
            start_time=datetime.now(),
            configuration_summary=config_summary,
            system_info=self._get_system_info()
        )
        
        logger.info(f"Started E2E test session: {test_session_id}")
        return self.current_report
    
    def start_test(self, scenario: TestScenario, storage_targets: List[str]) -> TestMetrics:
        """Start tracking metrics for a test scenario."""
        metrics = TestMetrics(
            scenario_id=scenario.test_id,
            start_time=datetime.now(),
            storage_targets_tested=storage_targets.copy()
        )
        
        logger.info(f"Started test for scenario: {scenario.test_id}")
        return metrics
    
    def finish_test(self, metrics: TestMetrics, success: bool, error_message: Optional[str] = None):
        """Finish tracking metrics for a test scenario."""
        metrics.finish(success, error_message)
        
        if self.current_report:
            self.current_report.add_test_metrics(metrics)
        
        status = "PASSED" if success else "FAILED"
        logger.info(f"Finished test for scenario {metrics.scenario_id}: {status}")
    
    def finish_session(self) -> Optional[E2ETestReport]:
        """Finish the current test session and generate reports."""
        if not self.current_report:
            logger.warning("No active test session to finish")
            return None
        
        self.current_report.finalize()
        
        # Generate reports
        self._generate_console_report()
        self._generate_json_report()
        self._generate_html_report()
        
        logger.info(f"Finished E2E test session: {self.current_report.test_session_id}")
        return self.current_report
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for the report."""
        import platform
        import sys
        
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_console_report(self):
        """Generate console output report."""
        if not self.current_report:
            return
        
        report = self.current_report
        
        print("\n" + "=" * 80)
        print(f"E2E TEST RESULTS - {report.test_session_id}")
        print("=" * 80)
        
        # Overall summary
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   Status: {'✅ PASSED' if report.overall_success else '❌ FAILED'}")
        print(f"   Success Rate: {report.success_rate:.1%} ({report.successful_scenarios}/{report.total_scenarios})")
        print(f"   Duration: {report.total_duration_ms:.0f}ms")
        print(f"   Failed: {report.failed_scenarios}")
        print(f"   Skipped: {report.skipped_scenarios}")
        
        # Scenario details
        print(f"\n📋 SCENARIO RESULTS:")
        for scenario_id, metrics in report.test_metrics.items():
            status = "✅ PASS" if metrics.success else "❌ FAIL"
            duration = f"{metrics.duration_ms:.0f}ms"
            targets = ", ".join(metrics.storage_targets_tested)
            
            print(f"   {status} {scenario_id:<20} ({duration:>6}) - {targets}")
            
            if metrics.error_messages:
                for error in metrics.error_messages[:2]:  # Show first 2 errors
                    print(f"      ❌ {error}")
            
            if metrics.warnings:
                for warning in metrics.warnings[:2]:  # Show first 2 warnings
                    print(f"      ⚠️  {warning}")
        
        # Performance summary
        if report.test_metrics:
            total_ingestion_time = sum(
                m.ingestion_time_ms or 0 for m in report.test_metrics.values()
            )
            total_retrieval_time = sum(
                m.retrieval_time_ms or 0 for m in report.test_metrics.values()
            )
            total_chunks_ingested = sum(
                m.chunks_ingested for m in report.test_metrics.values()
            )
            total_chunks_retrieved = sum(
                m.chunks_retrieved for m in report.test_metrics.values()
            )
            
            print(f"\n⏱️  PERFORMANCE SUMMARY:")
            print(f"   Total Ingestion Time: {total_ingestion_time:.0f}ms")
            print(f"   Total Retrieval Time: {total_retrieval_time:.0f}ms")
            print(f"   Chunks Ingested: {total_chunks_ingested}")
            print(f"   Chunks Retrieved: {total_chunks_retrieved}")
        
        # Configuration summary
        print(f"\n⚙️  CONFIGURATION:")
        config = report.configuration_summary
        print(f"   Storage Targets: {list(config.get('storage_targets', {}).keys())}")
        print(f"   Scenarios Available: {list(config.get('scenarios', []))}")
        
        print("\n" + "=" * 80)
    
    def _generate_json_report(self):
        """Generate JSON report file."""
        if not self.current_report:
            return
        
        # Convert report to JSON-serializable format
        report_data = asdict(self.current_report)
        
        # Handle datetime serialization
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        # Convert datetime fields
        for key, value in report_data.items():
            if isinstance(value, datetime):
                report_data[key] = value.isoformat()
        
        # Convert test metrics datetime fields
        for metrics_data in report_data.get('test_metrics', {}).values():
            for key, value in metrics_data.items():
                if isinstance(value, datetime):
                    metrics_data[key] = value.isoformat()
        
        # Write JSON report
        json_file = self.output_dir / f"e2e_report_{self.current_report.test_session_id}.json"
        
        try:
            with open(json_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=serialize_datetime)
            
            logger.info(f"Generated JSON report: {json_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")
    
    def _generate_html_report(self):
        """Generate HTML report file."""
        if not self.current_report:
            return
        
        html_file = self.output_dir / f"e2e_report_{self.current_report.test_session_id}.html"
        
        try:
            html_content = self._create_html_content()
            
            with open(html_file, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Generated HTML report: {html_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
    
    def _create_html_content(self) -> str:
        """Create HTML content for the report."""
        if not self.current_report:
            return ""
        
        report = self.current_report
        
        # Simple HTML template
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>E2E Test Report - {report.test_session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .scenario {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }}
        .pass {{ border-left-color: #4CAF50; }}
        .fail {{ border-left-color: #f44336; }}
        .error {{ color: #f44336; font-size: 0.9em; }}
        .warning {{ color: #ff9800; font-size: 0.9em; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>E2E Test Report</h1>
        <p><strong>Session ID:</strong> {report.test_session_id}</p>
        <p><strong>Status:</strong> {'PASSED' if report.overall_success else 'FAILED'}</p>
        <p><strong>Success Rate:</strong> {report.success_rate:.1%}</p>
        <p><strong>Duration:</strong> {report.total_duration_ms:.0f}ms</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Scenarios</td><td>{report.total_scenarios}</td></tr>
            <tr><td>Successful</td><td>{report.successful_scenarios}</td></tr>
            <tr><td>Failed</td><td>{report.failed_scenarios}</td></tr>
            <tr><td>Skipped</td><td>{report.skipped_scenarios}</td></tr>
        </table>
    </div>
    
    <div class="scenarios">
        <h2>Scenario Results</h2>
        """
        
        for scenario_id, metrics in report.test_metrics.items():
            status_class = "pass" if metrics.success else "fail"
            status_text = "PASSED" if metrics.success else "FAILED"
            
            html += f"""
        <div class="scenario {status_class}">
            <h3>{scenario_id} - {status_text}</h3>
            <p><strong>Duration:</strong> {metrics.duration_ms:.0f}ms</p>
            <p><strong>Storage Targets:</strong> {', '.join(metrics.storage_targets_tested)}</p>
            <p><strong>Chunks Ingested:</strong> {metrics.chunks_ingested}</p>
            <p><strong>Chunks Retrieved:</strong> {metrics.chunks_retrieved}</p>
            """
            
            if metrics.error_messages:
                html += "<div class='error'><strong>Errors:</strong><ul>"
                for error in metrics.error_messages:
                    html += f"<li>{error}</li>"
                html += "</ul></div>"
            
            if metrics.warnings:
                html += "<div class='warning'><strong>Warnings:</strong><ul>"
                for warning in metrics.warnings:
                    html += f"<li>{warning}</li>"
                html += "</ul></div>"
            
            html += "</div>"
        
        html += """
    </div>
</body>
</html>
        """
        
        return html


def generate_summary_report(reports: List[E2ETestReport], output_file: Optional[str] = None):
    """
    Generate a summary report across multiple test sessions.
    
    Args:
        reports: List of E2ETestReport objects
        output_file: Optional output file path
    """
    if not reports:
        logger.warning("No reports provided for summary")
        return
    
    # Calculate aggregate metrics
    total_scenarios = sum(r.total_scenarios for r in reports)
    total_successful = sum(r.successful_scenarios for r in reports)
    total_failed = sum(r.failed_scenarios for r in reports)
    
    overall_success_rate = total_successful / total_scenarios if total_scenarios > 0 else 0.0
    
    print(f"\n📊 AGGREGATE SUMMARY ({len(reports)} test sessions):")
    print(f"   Overall Success Rate: {overall_success_rate:.1%}")
    print(f"   Total Scenarios: {total_scenarios}")
    print(f"   Total Successful: {total_successful}")
    print(f"   Total Failed: {total_failed}")
    
    # Show per-session summary
    print(f"\n📋 PER-SESSION SUMMARY:")
    for report in reports:
        status = "✅" if report.overall_success else "❌"
        print(f"   {status} {report.test_session_id}: {report.success_rate:.1%} ({report.successful_scenarios}/{report.total_scenarios})")


# Global reporter instance
_reporter: Optional[E2EReporter] = None


def get_reporter(output_dir: Optional[str] = None) -> E2EReporter:
    """Get or create global reporter instance."""
    global _reporter
    if _reporter is None:
        _reporter = E2EReporter(output_dir)
    return _reporter 