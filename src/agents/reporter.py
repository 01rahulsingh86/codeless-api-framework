import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..core.models import TestResult
from ..reporter.html_reporter import HTMLReporter
from .planner import ExecutionPlan


class TestReporter:
    """Generates reports and handles result notifications."""
    
    def __init__(self, plan: ExecutionPlan):
        self.plan = plan
        self.html_reporter = HTMLReporter()
        
        # Create output directory
        self.output_dir = Path(plan.config.get('reporting', {}).get('output_directory', 'reports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_reports(self, results: List[TestResult], 
                        suite_name: str = None) -> Dict[str, str]:
        """Generate all configured reports."""
        
        suite_name = suite_name or f"test_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_paths = {}
        
        # Generate HTML report
        if self.plan.config.get('reporting', {}).get('html', True):
            html_path = self._generate_html_report(results, suite_name)
            report_paths['html'] = html_path
        
        # Generate JSON report
        if self.plan.config.get('reporting', {}).get('json', True):
            json_path = self._generate_json_report(results, suite_name)
            report_paths['json'] = json_path
        
        # Generate JUnit XML for CI/CD systems
        if self.plan.config.get('reporting', {}).get('junit', False):
            junit_path = self._generate_junit_report(results, suite_name)
            report_paths['junit'] = junit_path
        
        # Generate summary metrics
        summary_path = self._generate_summary_report(results, suite_name)
        report_paths['summary'] = summary_path
        
        return report_paths
    
    def _generate_html_report(self, results: List[TestResult], suite_name: str) -> str:
        """Generate HTML report."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{suite_name}_report_{timestamp}.html"
        output_path = self.output_dir / filename
        
        return self.html_reporter.generate_report(
            test_results=results,
            suite_name=suite_name,
            output_path=str(output_path),
            environment=self.plan.environment
        )
    
    def _generate_json_report(self, results: List[TestResult], suite_name: str) -> str:
        """Generate JSON report for programmatic access."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{suite_name}_report_{timestamp}.json"
        output_path = self.output_dir / filename
        
        return self.html_reporter.generate_json_report(
            test_results=results,
            suite_name=suite_name,
            output_path=str(output_path)
        )
    
    def _generate_junit_report(self, results: List[TestResult], suite_name: str) -> str:
        """Generate JUnit XML report for CI/CD integration."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{suite_name}_junit_{timestamp}.xml"
        output_path = self.output_dir / filename
        
        # Calculate statistics
        total_tests = len(results)
        failures = sum(1 for r in results if r.status.value == 'failed')
        errors = 0  # We'll categorize all as failures for now
        total_time = sum(
            (r.end_time - r.start_time).total_seconds()
            for r in results
            if r.end_time
        )
        
        # Generate JUnit XML
        xml_content = f'<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += f'<testsuite name="{suite_name}" tests="{total_tests}" '
        xml_content += f'failures="{failures}" errors="{errors}" time="{total_time:.3f}">\n'
        
        for result in results:
            test_time = (result.end_time - result.start_time).total_seconds() if result.end_time else 0
            
            xml_content += f'  <testcase name="{result.test_name}" time="{test_time:.3f}">\n'
            
            if result.status.value == 'failed':
                xml_content += f'    <failure message="{result.error_message or "Test failed"}">\n'
                xml_content += f'      {result.error_message or "No error details available"}\n'
                xml_content += f'    </failure>\n'
            
            xml_content += f'  </testcase>\n'
        
        xml_content += '</testsuite>\n'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        return str(output_path)
    
    def _generate_summary_report(self, results: List[TestResult], suite_name: str) -> str:
        """Generate a summary report with key metrics."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{suite_name}_summary_{timestamp}.txt"
        output_path = self.output_dir / filename
        
        # Calculate statistics
        total_tests = len(results)
        passed = sum(1 for r in results if r.status.value == 'passed')
        failed = sum(1 for r in results if r.status.value == 'failed')
        skipped = sum(1 for r in results if r.status.value == 'skipped')
        
        total_time = sum(
            (r.end_time - r.start_time).total_seconds()
            for r in results
            if r.end_time
        )
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        # Generate summary content
        summary_content = f"""
API Test Execution Summary
=========================
Suite: {suite_name}
Environment: {self.plan.environment.get('name', 'default')}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Results Summary
---------------
Total Tests: {total_tests}
Passed: {passed}
Failed: {failed}
Skipped: {skipped}
Success Rate: {success_rate:.1f}%
Total Execution Time: {total_time:.2f}s
Average Test Time: {total_time/total_tests:.2f}s

Failed Tests
------------
"""
        
        failed_tests = [r for r in results if r.status.value == 'failed']
        if failed_tests:
            for i, result in enumerate(failed_tests, 1):
                summary_content += f"{i}. {result.test_name}\n"
                if result.error_message:
                    summary_content += f"   Error: {result.error_message}\n"
                summary_content += "\n"
        else:
            summary_content += "No failed tests!\n"
        
        summary_content += f"""
Test Files Processed
-------------------
"""
        for test_file in self.plan.test_files:
            summary_content += f"- {test_file}\n"
        
        summary_content += f"""
Environment Configuration
-------------------------
"""
        for key, value in self.plan.environment.get('variables', {}).items():
            summary_content += f"{key}: {value}\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        return str(output_path)
    
    def send_notifications(self, results: List[TestResult], report_paths: Dict[str, str]):
        """Send notifications based on configuration."""
        
        notification_config = self.plan.config.get('notifications', {})
        
        # Send Slack notification if configured
        if notification_config.get('slack'):
            self._send_slack_notification(results, report_paths, notification_config['slack'])
        
        # Send email notification if configured
        if notification_config.get('email'):
            self._send_email_notification(results, report_paths, notification_config['email'])
        
        # Send Teams notification if configured
        if notification_config.get('teams'):
            self._send_teams_notification(results, report_paths, notification_config['teams'])
    
    def _send_slack_notification(self, results: List[TestResult], report_paths: Dict[str, str], config: Dict[str, Any]):
        """Send Slack notification (placeholder implementation)."""
        
        # Calculate statistics
        total_tests = len(results)
        passed = sum(1 for r in results if r.status.value == 'passed')
        failed = sum(1 for r in results if r.status.value == 'failed')
        
        # Create Slack message
        color = 'good' if failed == 0 else 'danger'
        message = {
            "attachments": [
                {
                    "color": color,
                    "title": "API Test Results",
                    "fields": [
                        {
                            "title": "Total Tests",
                            "value": str(total_tests),
                            "short": True
                        },
                        {
                            "title": "Passed",
                            "value": str(passed),
                            "short": True
                        },
                        {
                            "title": "Failed",
                            "value": str(failed),
                            "short": True
                        },
                        {
                            "title": "Success Rate",
                            "value": f"{(passed/total_tests*100):.1f}%" if total_tests > 0 else "0%",
                            "short": True
                        }
                    ],
                    "footer": "Codeless API Framework",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        # Add HTML report link if available
        if 'html' in report_paths:
            html_path = Path(report_paths['html'])
            if html_path.exists():
                # Convert to absolute path or URL as needed
                message["attachments"][0]["title_link"] = f"file://{html_path.absolute()}"
        
        # This would integrate with Slack API
        print(f"Slack notification would be sent: {json.dumps(message, indent=2)}")
    
    def _send_email_notification(self, results: List[TestResult], report_paths: Dict[str, str], config: Dict[str, Any]):
        """Send email notification (placeholder implementation)."""
        
        total_tests = len(results)
        passed = sum(1 for r in results if r.status.value == 'passed')
        failed = sum(1 for r in results if r.status.value == 'failed')
        
        subject = f"API Test Results - {passed}/{total_tests} passed"
        
        body = f"""
API Test Execution Complete

Total Tests: {total_tests}
Passed: {passed}
Failed: {failed}
Success Rate: {(passed/total_tests*100):.1f}%

Reports:
"""
        
        for report_type, path in report_paths.items():
            body += f"- {report_type.upper()}: {path}\n"
        
        print(f"Email notification would be sent:\nSubject: {subject}\nBody: {body}")
    
    def _send_teams_notification(self, results: List[TestResult], report_paths: Dict[str, str], config: Dict[str, Any]):
        """Send Microsoft Teams notification (placeholder implementation)."""
        
        total_tests = len(results)
        passed = sum(1 for r in results if r.status.value == 'passed')
        failed = sum(1 for r in results if r.status.value == 'failed')
        
        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "00FF00" if failed == 0 else "FF0000",
            "summary": "API Test Results",
            "sections": [
                {
                    "activityTitle": "API Test Execution Complete",
                    "activitySubtitle": f"Results: {passed}/{total_tests} tests passed",
                    "facts": [
                        {"name": "Total Tests", "value": str(total_tests)},
                        {"name": "Passed", "value": str(passed)},
                        {"name": "Failed", "value": str(failed)},
                        {"name": "Success Rate", "value": f"{(passed/total_tests*100):.1f}%" if total_tests > 0 else "0%"}
                    ],
                    "markdown": True
                }
            ]
        }
        
        print(f"Teams notification would be sent: {json.dumps(message, indent=2)}")
    
    def archive_reports(self, report_paths: Dict[str, str], archive_dir: str = None):
        """Archive reports to specified directory."""
        
        if archive_dir is None:
            archive_dir = self.output_dir / "archive"
        
        archive_path = Path(archive_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m')
        month_archive = archive_path / timestamp
        month_archive.mkdir(exist_ok=True)
        
        for report_type, path in report_paths.items():
            source = Path(path)
            if source.exists():
                target = month_archive / source.name
                source.rename(target)
                print(f"Archived {report_type} report to {target}")
    
    def get_metrics(self, results: List[TestResult]) -> Dict[str, Any]:
        """Extract metrics from test results for monitoring systems."""
        
        total_tests = len(results)
        passed = sum(1 for r in results if r.status.value == 'passed')
        failed = sum(1 for r in results if r.status.value == 'failed')
        skipped = sum(1 for r in results if r.status.value == 'skipped')
        
        total_time = sum(
            (r.end_time - r.start_time).total_seconds()
            for r in results
            if r.end_time
        )
        
        # Calculate step-level metrics
        total_steps = sum(len(r.steps) for r in results)
        passed_steps = sum(
            len([s for s in r.steps if s.get('status') == 'passed'])
            for r in results
        )
        failed_steps = sum(
            len([s for s in r.steps if s.get('status') == 'failed'])
            for r in results
        )
        
        return {
            'test_metrics': {
                'total_tests': total_tests,
                'passed_tests': passed,
                'failed_tests': failed,
                'skipped_tests': skipped,
                'success_rate': (passed / total_tests * 100) if total_tests > 0 else 0,
                'total_execution_time': total_time,
                'average_test_time': total_time / total_tests if total_tests > 0 else 0
            },
            'step_metrics': {
                'total_steps': total_steps,
                'passed_steps': passed_steps,
                'failed_steps': failed_steps,
                'step_success_rate': (passed_steps / total_steps * 100) if total_steps > 0 else 0
            },
            'environment': self.plan.environment.get('name', 'default'),
            'timestamp': datetime.now().isoformat()
        }
