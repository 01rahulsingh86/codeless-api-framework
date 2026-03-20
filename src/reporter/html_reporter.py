import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template

from ..core.models import TestResult, TestReport, TestStatus


class HTMLReporter:
    """Generates beautiful HTML reports for test results."""
    
    def __init__(self, template_dir: str = None):
        self.template_dir = template_dir or Path(__file__).parent / "templates"
        self.template = self._get_template()
    
    def _get_template(self) -> Template:
        """Get or create the HTML template."""
        template_path = self.template_dir / "report_template.html"
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        else:
            template_content = self._get_default_template()
            # Ensure template directory exists
            self.template_dir.mkdir(parents=True, exist_ok=True)
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
        
        return Template(template_content)
    
    def _get_default_template(self) -> str:
        """Get the default HTML template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Test Report - {{ report.suite_name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }
        
        .summary-card:hover {
            transform: translateY(-2px);
        }
        
        .summary-card h3 {
            font-size: 2em;
            margin-bottom: 5px;
        }
        
        .summary-card.total h3 { color: #667eea; }
        .summary-card.passed h3 { color: #10b981; }
        .summary-card.failed h3 { color: #ef4444; }
        .summary-card.skipped h3 { color: #f59e0b; }
        
        .summary-card p {
            color: #666;
            font-weight: 500;
        }
        
        .test-controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .control-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .control-btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .control-btn.expand-all {
            background: #10b981;
            color: white;
        }
        
        .control-btn.collapse-all {
            background: #f59e0b;
            color: white;
        }
        
        .control-btn.filter-passed {
            background: #e5e7eb;
            color: #374151;
        }
        
        .control-btn.filter-failed {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .control-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .search-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .search-input {
            padding: 8px 12px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
            min-width: 200px;
        }
        
        .test-results {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .test-header {
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .test-header h2 {
            color: #495057;
            margin-bottom: 0;
        }
        
        .test-stats {
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: #666;
        }
        
        .test-item {
            border-bottom: 1px solid #e9ecef;
        }
        
        .test-item:last-child {
            border-bottom: none;
        }
        
        .test-item.hidden {
            display: none;
        }
        
        .test-name {
            padding: 20px;
            background: #f8f9fa;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background-color 0.2s;
        }
        
        .test-name:hover {
            background: #e9ecef;
        }
        
        .test-name h3 {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 0;
        }
        
        .test-info {
            display: flex;
            align-items: center;
            gap: 15px;
            font-size: 14px;
            color: #666;
        }
        
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-badge.passed {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-badge.failed {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .status-badge.skipped {
            background: #fed7aa;
            color: #92400e;
        }
        
        .test-details {
            display: none;
            padding: 20px;
            background: white;
        }
        
        .test-details.active {
            display: block;
        }
        
        .step-item {
            margin-bottom: 20px;
            padding: 15px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
        }
        
        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .step-name {
            font-weight: 600;
            color: #495057;
        }
        
        .step-status {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }
        
        .step-status.passed {
            background: #d1fae5;
            color: #065f46;
        }
        
        .step-status.failed {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .step-details {
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 0.9em;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .request-details, .response-details {
            margin-bottom: 15px;
        }
        
        .request-details h4, .response-details h4 {
            color: #667eea;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .json-content {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 12px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 0.85em;
            line-height: 1.4;
            white-space: pre-wrap;
            overflow-x: auto;
        }
        
        .json-key { color: #9cdcfe; }
        .json-string { color: #ce9178; }
        .json-number { color: #b5cea8; }
        .json-boolean { color: #569cd6; }
        .json-null { color: #808080; }
        
        .test-case-separator {
            background: #f0f9ff;
            border-left: 4px solid #3b82f6;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 4px;
            font-style: italic;
            color: #64748b;
        }
        
        .execution-time {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        
        .error-message {
            background: #fee2e2;
            color: #991b1b;
            padding: 12px;
            border-radius: 4px;
            margin-top: 10px;
            border-left: 4px solid #ef4444;
        }
        
        .toggle-icon {
            transition: transform 0.2s;
            font-size: 12px;
        }
        
        .toggle-icon.rotated {
            transform: rotate(90deg);
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            border-top: 1px solid #e9ecef;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #10b981 var(--passed-percentage), #ef4444 var(--passed-percentage), #ef4444 var(--total-percentage));
            transition: width 0.3s ease;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .summary {
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            }
            
            .summary-card {
                padding: 20px;
            }
            
            .test-controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .control-buttons {
                justify-content: center;
            }
            
            .search-box {
                justify-content: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>API Test Report</h1>
            <div class="subtitle">
                Suite: {{ report.suite_name }} | 
                Generated: {{ report.generated_at.strftime('%Y-%m-%d %H:%M:%S') }} |
                Duration: {{ "%.2f"|format(report.total_time) }}s
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="--passed-percentage: {{ (report.passed / report.total_tests * 100)|round(1) }}%; --total-percentage: 100%;"></div>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card total">
                <h3>{{ report.total_tests }}</h3>
                <p>Total Tests</p>
            </div>
            <div class="summary-card passed">
                <h3>{{ report.passed }}</h3>
                <p>Passed</p>
            </div>
            <div class="summary-card failed">
                <h3>{{ report.failed }}</h3>
                <p>Failed</p>
            </div>
            <div class="summary-card skipped">
                <h3>{{ report.skipped }}</h3>
                <p>Skipped</p>
            </div>
        </div>
        
        <div class="test-controls">
            <div class="control-buttons">
                <button class="control-btn expand-all" onclick="expandAllTests()">Expand All</button>
                <button class="control-btn collapse-all" onclick="collapseAllTests()">Collapse All</button>
                <button class="control-btn filter-passed" onclick="filterTests('passed')">Show Passed</button>
                <button class="control-btn filter-failed" onclick="filterTests('failed')">Show Failed</button>
                <button class="control-btn filter-passed" onclick="filterTests('all')">Show All</button>
            </div>
            <div class="search-box">
                <input type="text" class="search-input" placeholder="Search tests..." onkeyup="searchTests(this.value)">
            </div>
        </div>
        
        <div class="test-results">
            <div class="test-header">
                <h2>Test Results</h2>
                <div class="test-stats">
                    <span>{{ report.total_tests }} tests</span>
                    <span>{{ "%.1f"|format(report.passed / report.total_tests * 100) }}% pass rate</span>
                    <span>{{ "%.2f"|format(report.total_time) }}s total</span>
                </div>
            </div>
            
            {% for result in report.test_results %}
            <div class="test-item" data-status="{{ result.status.value }}">
                <div class="test-name" onclick="toggleTestDetails('test-{{ loop.index }}')">
                    <h3>
                        <span class="toggle-icon" id="icon-test-{{ loop.index }}">▶</span>
                        {{ result.test_name }}
                    </h3>
                    <div class="test-info">
                        <span class="status-badge {{ result.status.value }}">{{ result.status.value }}</span>
                        {% if result.end_time %}
                        <span>{{ "%.3f"|format((result.end_time - result.start_time).total_seconds()) }}s</span>
                        {% endif %}
                        {% if result.steps %}
                        <span>{{ result.steps|length }} steps</span>
                        {% endif %}
                    </div>
                </div>
                
                <div class="test-details" id="test-{{ loop.index }}">
                    {% if result.error_message %}
                    <div class="error-message">
                        <strong>Error:</strong> {{ result.error_message }}
                    </div>
                    {% endif %}
                    
                    {% for step in result.steps %}
                    <div class="step-item">
                        <div class="step-header">
                            <span class="step-name">{{ step.name }}</span>
                            <span class="step-status {{ step.status }}">{{ step.status }}</span>
                        </div>
                        
                        {% if step.execution_time %}
                        <div class="execution-time">
                            Execution time: {{ "%.3f"|format(step.execution_time) }}s
                        </div>
                        {% endif %}
                        
                        {% if step.get('is_test_case_header') %}
                        <div class="test-case-separator">
                            <em>Test case with {{ step.get('steps_count', 0) }} steps</em>
                        </div>
                        {% endif %}
                        
                        {% if step.request %}
                        <div class="request-details">
                            <h4>📤 Request</h4>
                            <div class="step-details">
                                <div><strong>{{ step.request.method }}</strong> {{ step.request.url }}</div>
                                {% if step.request.headers %}
                                <div><strong>Headers:</strong></div>
                                <div class="json-content">{{ format_json(step.request.headers) }}</div>
                                {% endif %}
                                {% if step.request.body %}
                                <div><strong>Body:</strong></div>
                                <div class="json-content">{{ format_json(step.request.body) }}</div>
                                {% endif %}
                            </div>
                        </div>
                        {% endif %}
                        
                        {% if step.response %}
                        <div class="response-details">
                            <h4>📥 Response</h4>
                            <div class="step-details">
                                <div><strong>Status:</strong> {{ step.response.status_code }}</div>
                                <div><strong>Response Time:</strong> {{ "%.3f"|format(step.response.response_time) }}s</div>
                                {% if step.response.headers %}
                                <div><strong>Headers:</strong></div>
                                <div class="json-content">{{ format_json(step.response.headers) }}</div>
                                {% endif %}
                                <div><strong>Body:</strong></div>
                                <div class="json-content">{{ format_json(step.response.body) }}</div>
                            </div>
                        </div>
                        {% endif %}
                        
                        {% if step.error %}
                        <div class="error-message">
                            <strong>Error:</strong> {{ step.error }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Generated by Codeless API Framework | {{ report.generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
        </div>
    </div>
    
    <script>
        function toggleTestDetails(testId) {
            const details = document.getElementById(testId);
            const icon = document.getElementById('icon-' + testId);
            
            if (details.classList.contains('active')) {
                details.classList.remove('active');
                icon.classList.remove('rotated');
            } else {
                details.classList.add('active');
                icon.classList.add('rotated');
            }
        }
        
        function expandAllTests() {
            document.querySelectorAll('.test-details').forEach(details => {
                details.classList.add('active');
            });
            document.querySelectorAll('.toggle-icon').forEach(icon => {
                icon.classList.add('rotated');
            });
        }
        
        function collapseAllTests() {
            document.querySelectorAll('.test-details').forEach(details => {
                details.classList.remove('active');
            });
            document.querySelectorAll('.toggle-icon').forEach(icon => {
                icon.classList.remove('rotated');
            });
        }
        
        function filterTests(status) {
            const testItems = document.querySelectorAll('.test-item');
            
            testItems.forEach(item => {
                if (status === 'all') {
                    item.classList.remove('hidden');
                } else if (status === 'passed' && item.dataset.status === 'passed') {
                    item.classList.remove('hidden');
                } else if (status === 'failed' && item.dataset.status === 'failed') {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        }
        
        function searchTests(searchTerm) {
            const testItems = document.querySelectorAll('.test-item');
            const term = searchTerm.toLowerCase();
            
            testItems.forEach(item => {
                const testName = item.querySelector('h3').textContent.toLowerCase();
                if (testName.includes(term)) {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        }
        
        // Auto-expand failed tests
        document.addEventListener('DOMContentLoaded', function() {
            const failedTests = document.querySelectorAll('.status-badge.failed');
            failedTests.forEach(badge => {
                const testItem = badge.closest('.test-item');
                const testDetails = testItem.querySelector('.test-details');
                const icon = testItem.querySelector('.toggle-icon');
                
                if (testDetails && icon) {
                    testDetails.classList.add('active');
                    icon.classList.add('rotated');
                }
            });
        });
        
        // JSON pretty printing function
        function prettyPrintJSON(obj) {
            return JSON.stringify(obj, null, 2)
                .replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:')
                .replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>')
                .replace(/: (\\d+)/g, ': <span class="json-number">$1</span>')
                .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>')
                .replace(/: null/g, ': <span class="json-null">null</span>');
        }
    </script>
</body>
</html>
        """
    
    def _format_json_pretty(self, data) -> str:
        """Format JSON data with proper pretty printing and syntax highlighting."""
        if data is None:
            return "null"
        
        try:
            # Convert to JSON string with proper formatting
            json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            
            # Apply syntax highlighting
            json_str = json_str.replace(r'"([^"]+)":', r'<span class="json-key">"\1"</span>:')
            json_str = json_str.replace(r': "([^"]*)"', r': <span class="json-string">"\1"</span>')
            json_str = json_str.replace(r': (\d+\.?\d*)', r': <span class="json-number">\1</span>')
            json_str = json_str.replace(r': (true|false)', r': <span class="json-boolean">\1</span>')
            json_str = json_str.replace(r': null', r': <span class="json-null">null</span>')
            
            return json_str
        except Exception:
            return str(data)
    
    def generate_report(self, test_results: List[TestResult], suite_name: str, 
                       output_path: str = None, environment: Dict[str, Any] = None) -> str:
        """Generate HTML report from test results."""
        
        # Calculate statistics
        total_tests = len(test_results)
        passed = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in test_results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in test_results if r.status == TestStatus.SKIPPED)
        
        # Calculate total time
        total_time = sum(
            (r.end_time - r.start_time).total_seconds() 
            for r in test_results 
            if r.end_time
        )
        
        # Create report object
        report = TestReport(
            suite_name=suite_name,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            total_time=total_time,
            test_results=test_results,
            environment=environment or {}
        )
        
        # Generate HTML
        html_content = self.template.render(
            report=report,
            format_json=self._format_json_pretty,
            tojson_pretty=lambda x: json.dumps(x, indent=2, ensure_ascii=False, default=str)
        )
        
        # Save to file
        if output_path is None:
            output_path = f"reports/{suite_name}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def generate_json_report(self, test_results: List[TestResult], suite_name: str, 
                           output_path: str = None) -> str:
        """Generate JSON report for programmatic access."""
        
        # Convert results to serializable format
        serializable_results = []
        for result in test_results:
            serializable_result = {
                'test_name': result.test_name,
                'status': result.status.value,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'error_message': result.error_message,
                'variables': result.variables,
                'steps': []
            }
            
            for step in result.steps:
                # Convert datetime objects to strings
                if 'request' in step and 'timestamp' in step['request']:
                    step['request']['timestamp'] = step['request']['timestamp'].isoformat()
                
                serializable_result['steps'].append(step)
            
            serializable_results.append(serializable_result)
        
        report_data = {
            'suite_name': suite_name,
            'generated_at': datetime.now().isoformat(),
            'results': serializable_results
        }
        
        # Save to file with pretty printing
        if output_path is None:
            output_path = f"reports/{suite_name}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        return output_path
