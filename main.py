#!/usr/bin/env python3
"""
Codeless API Automation Framework

Main entry point for running API tests from natural language definitions.
"""

import click
import sys
from pathlib import Path
from typing import List, Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.planner import TestPlanner
from src.agents.executor import TestExecutor
from src.agents.reporter import TestReporter


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Codeless API Automation Framework - Write API tests in natural language."""
    pass


@cli.command()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--environment', '-e', default='default', help='Environment configuration')
@click.option('--tests', '-t', multiple=True, help='Specific test files to run')
@click.option('--output', '-o', help='Output directory for reports')
@click.option('--parallel', is_flag=True, help='Enable parallel execution')
@click.option('--fail-fast', is_flag=True, help='Stop on first failure')
def run(config, environment, tests, output, parallel, fail_fast):
    """Run API tests from natural language definitions."""
    
    try:
        # Create execution plan
        planner = TestPlanner(config)
        plan = planner.create_execution_plan(
            test_paths=list(tests) if tests else None,
            environment=environment
        )
        
        # Override plan with CLI options
        if output:
            plan.config['reporting']['output_directory'] = output
        if parallel:
            plan.config['parallel_execution'] = True
        if fail_fast:
            plan.config['fail_fast'] = True
        
        # Validate plan
        issues = planner.validate_plan(plan)
        if issues:
            click.echo("Plan validation issues:", err=True)
            for issue in issues:
                click.echo(f"  - {issue}", err=True)
            sys.exit(1)
        
        click.echo(f"Executing {len(plan.test_files)} test files...")
        
        # Execute tests
        executor = TestExecutor(plan)
        results = executor.execute_plan()
        
        # Generate reports
        reporter = TestReporter(plan)
        report_paths = reporter.generate_reports(results)
        
        # Display summary
        summary = executor.get_execution_summary(results)
        click.echo(f"\nExecution Summary:")
        click.echo(f"  Total Tests: {summary['total_tests']}")
        click.echo(f"  Passed: {summary['passed']}")
        click.echo(f"  Failed: {summary['failed']}")
        click.echo(f"  Success Rate: {summary['success_rate']:.1f}%")
        click.echo(f"  Total Time: {summary['total_time']:.2f}s")
        
        # Show report paths
        click.echo(f"\nReports generated:")
        for report_type, path in report_paths.items():
            click.echo(f"  {report_type.upper()}: {path}")
        
        # Send notifications if configured
        if plan.config.get('notifications'):
            reporter.send_notifications(results, report_paths)
        
        # Exit with appropriate code
        if summary['failed'] > 0:
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--output', '-o', help='Output path for execution plan')
def plan(config, output):
    """Create and display execution plan without running tests."""
    
    try:
        planner = TestPlanner(config)
        execution_plan = planner.create_execution_plan()
        
        if output:
            planner.save_plan(execution_plan, output)
            click.echo(f"Execution plan saved to: {output}")
        else:
            # Display plan
            click.echo("Execution Plan:")
            click.echo(f"  Test Files: {len(execution_plan.test_files)}")
            click.echo(f"  Parallel Groups: {len(execution_plan.parallel_groups)}")
            
            for i, group in enumerate(execution_plan.parallel_groups, 1):
                click.echo(f"    Group {i}: {len(group)} files")
                for test_file in group:
                    click.echo(f"      - {test_file}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('test_file')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml']), default='json')
def validate(test_file, output_format):
    """Validate a test file syntax."""
    
    try:
        from src.parser import NLParser
        
        parser = NLParser()
        test_suite = parser.parse_file(test_file)
        
        click.echo(f"✓ Test file '{test_file}' is valid")
        click.echo(f"  Tests: {len(test_suite.tests)}")
        click.echo(f"  Global Setup: {len(test_suite.global_setup)} steps")
        click.echo(f"  Global Teardown: {len(test_suite.global_teardown)} steps")
        
        if output_format == 'json':
            import json
            click.echo("\nParsed structure:")
            click.echo(json.dumps({
                'name': test_suite.name,
                'tests_count': len(test_suite.tests),
                'config': test_suite.config
            }, indent=2))
    
    except Exception as e:
        click.echo(f"✗ Validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def init():
    """Initialize a new test project."""
    
    # Create directory structure
    directories = ['tests', 'config', 'reports', 'examples']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        click.echo(f"Created directory: {directory}")
    
    # Create sample configuration
    config_content = """
# Codeless API Framework Configuration

test_directory: tests
parallel_execution: true
max_parallel_tests: 5
timeout: 300
fail_fast: false
retry_failed_tests: false
retry_count: 2

# Global variables available in all tests
global_variables:
  base_url: "https://api.example.com"
  api_version: "v1"

# Environment configurations
environments:
  default:
    variables:
      base_url: "https://api.example.com"
  
  staging:
    variables:
      base_url: "https://staging-api.example.com"
  
  production:
    variables:
      base_url: "https://api.example.com"

# Reporting configuration
reporting:
  html: true
  json: true
  junit: false
  output_directory: reports

# Notification configuration (optional)
notifications:
  slack:
    webhook_url: "YOUR_SLACK_WEBHOOK_URL"
  email:
    smtp_server: "smtp.example.com"
    from_address: "tests@example.com"
    to_addresses: ["team@example.com"]
"""
    
    with open('config/framework.yml', 'w') as f:
        f.write(config_content)
    
    click.echo("Created configuration file: config/framework.yml")
    
    # Create sample test
    sample_test = """
Test: User Authentication Flow
Description: Test user login and token refresh

- Login User: POST {{base_url}}/auth/login
  Headers:
    Content-Type: application/json
  Body:
    username: testuser
    password: testpass
  Status code should be 200
  Extract access_token from response.access_token
  Extract user_id from response.user.id

- Get User Profile: GET {{base_url}}/users/{{user_id}}
  Headers:
    Authorization: Bearer {{access_token}}
  Status code should be 200
  Response should contain username

- Refresh Token: POST {{base_url}}/auth/refresh
  Headers:
    Authorization: Bearer {{access_token}}
  Status code should be 200
  Extract new_token from response.access_token
"""
    
    with open('tests/sample_test.txt', 'w') as f:
        f.write(sample_test)
    
    click.echo("Created sample test: tests/sample_test.txt")
    click.echo("\nProject initialized successfully!")
    click.echo("Run 'python main.py run' to execute the sample test.")


if __name__ == '__main__':
    cli()
