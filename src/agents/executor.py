import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional
from datetime import datetime
import traceback

from ..core.models import TestResult, TestStatus
from ..executor.api_executor import APIExecutor
from ..parser import NLParser
from .planner import ExecutionPlan


class TestExecutor:
    """Executes tests according to the execution plan."""
    
    def __init__(self, plan: ExecutionPlan):
        self.plan = plan
        self.parser = NLParser()
        self.executor = APIExecutor(
            timeout=plan.environment.get('timeout', 30),
            verify_ssl=plan.config.get('verify_ssl', True)
        )
        
        # Set global variables
        for name, value in plan.environment.get('variables', {}).items():
            self.executor.set_variable(name, value)
    
    def execute_plan(self) -> List[TestResult]:
        """Execute the entire test plan."""
        all_results = []
        
        try:
            # Execute tests in parallel groups
            for group in self.plan.parallel_groups:
                group_results = self._execute_parallel_group(group)
                all_results.extend(group_results)
                
                # Check if we should continue after failures
                if self._should_stop_execution(group_results):
                    break
            
            # Retry failed tests if configured
            if self.plan.config.get('retry_failed_tests', False):
                retry_results = self._retry_failed_tests(all_results)
                all_results.extend(retry_results)
        
        except Exception as e:
            # Create a failed result for the entire execution
            error_result = TestResult(
                test_name="Execution Error",
                status=TestStatus.FAILED,
                steps=[],
                start_time=datetime.now(),
                end_time=datetime.now(),
                error_message=f"Execution failed: {str(e)}"
            )
            all_results.append(error_result)
        
        return all_results
    
    def _execute_parallel_group(self, test_files: List[str]) -> List[TestResult]:
        """Execute a group of test files in parallel."""
        
        if len(test_files) == 1:
            # Single test, execute directly
            return [self._execute_test_file(test_files[0])]
        
        # Multiple tests, execute in parallel
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(test_files)) as executor:
            # Submit all tests for execution
            future_to_test = {
                executor.submit(self._execute_test_file, test_file): test_file 
                for test_file in test_files
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_test):
                test_file = future_to_test[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # Create failed result for this test
                    error_result = TestResult(
                        test_name=f"Error in {test_file}",
                        status=TestStatus.FAILED,
                        steps=[],
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        error_message=f"Test execution failed: {str(e)}\n{traceback.format_exc()}"
                    )
                    results.append(error_result)
        
        return results
    
    def _execute_test_file(self, test_file: str) -> TestResult:
        """Execute a single test file."""
        start_time = datetime.now()
        
        try:
            # Parse the test file
            test_suite = self.parser.parse_file(test_file)
            
            # Execute global setup
            if test_suite.global_setup:
                for step in test_suite.global_setup:
                    self.executor._execute_step(step, None)  # No result container for setup
            
            # Execute all tests in the suite
            test_results = []
            for test_case in test_suite.tests:
                # Reset executor variables for each test case
                self.executor.reset_variables()
                
                # Restore global variables
                for name, value in self.plan.environment.get('variables', {}).items():
                    self.executor.set_variable(name, value)
                
                # Execute the test case
                result = self.executor.execute_test_case(test_case)
                test_results.append(result)
            
            # Execute global teardown
            if test_suite.global_teardown:
                for step in test_suite.global_teardown:
                    try:
                        self.executor._execute_step(step, None)
                    except Exception:
                        # Don't fail the entire suite for teardown errors
                        pass
            
            # Create combined result for the test file
            overall_status = TestStatus.PASSED
            failed_tests = [r for r in test_results if r.status == TestStatus.FAILED]
            if failed_tests:
                overall_status = TestStatus.FAILED
            
            # Combine all steps from all test cases with their details
            all_steps = []
            for test_result in test_results:
                # Add a separator for each test case
                all_steps.append({
                    'name': f'Test Case: {test_result.test_name}',
                    'status': test_result.status.value,
                    'execution_time': (test_result.end_time - test_result.start_time).total_seconds() if test_result.end_time else 0,
                    'is_test_case_header': True
                })
                
                # Add all the actual steps with request/response details
                for step in test_result.steps:
                    step_copy = step.copy()
                    step_copy['test_case_name'] = test_result.test_name
                    all_steps.append(step_copy)
            
            # Create a summary result with full step details
            summary_result = TestResult(
                test_name=f"Suite: {test_suite.name}",
                status=overall_status,
                steps=all_steps,
                start_time=start_time,
                end_time=datetime.now(),
                error_message=f"Failed {len(failed_tests)} out of {len(test_results)} tests" if failed_tests else None
            )
            
            return summary_result
            
        except Exception as e:
            return TestResult(
                test_name=f"Failed to execute {test_file}",
                status=TestStatus.FAILED,
                steps=[],
                start_time=start_time,
                end_time=datetime.now(),
                error_message=f"Test file execution failed: {str(e)}\n{traceback.format_exc()}"
            )
    
    def _should_stop_execution(self, group_results: List[TestResult]) -> bool:
        """Determine if execution should stop based on results."""
        
        # Check if any tests failed
        failed_tests = [r for r in group_results if r.status == TestStatus.FAILED]
        
        # Stop if configured to fail fast and there are failures
        if self.plan.config.get('fail_fast', False) and failed_tests:
            return True
        
        return False
    
    def _retry_failed_tests(self, all_results: List[TestResult]) -> List[TestResult]:
        """Retry failed tests according to configuration."""
        retry_count = self.plan.config.get('retry_count', 2)
        retry_results = []
        
        # Find failed tests
        failed_results = [r for r in all_results if r.status == TestStatus.FAILED]
        
        for failed_result in failed_results:
            for attempt in range(retry_count):
                print(f"Retrying {failed_result.test_name} - Attempt {attempt + 1}")
                
                # Extract the test file from the result name
                test_file = self._extract_test_file_from_result(failed_result)
                if test_file:
                    retry_result = self._execute_test_file(test_file)
                    retry_results.append(retry_result)
                    
                    # If retry succeeded, break
                    if retry_result.status == TestStatus.PASSED:
                        break
        
        return retry_results
    
    def _extract_test_file_from_result(self, result: TestResult) -> Optional[str]:
        """Extract test file path from test result."""
        # This is a simplified extraction - in a real implementation,
        # you might want to store the test file in the result itself
        
        result_name = result.test_name
        
        # Look for matching test files in the plan
        for test_file in self.plan.test_files:
            if Path(test_file).stem in result_name:
                return test_file
        
        return None
    
    def get_execution_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Get a summary of execution results."""
        
        total_tests = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        
        total_time = sum(
            (r.end_time - r.start_time).total_seconds()
            for r in results
            if r.end_time
        )
        
        return {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'success_rate': (passed / total_tests * 100) if total_tests > 0 else 0,
            'total_time': total_time,
            'average_time': total_time / total_tests if total_tests > 0 else 0
        }
