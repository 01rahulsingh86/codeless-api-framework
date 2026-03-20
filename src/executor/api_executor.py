import requests
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

from ..core.models import (
    APIRequest, APIResponse, TestStep, TestCase, 
    TestResult, TestStatus
)
from ..core.assertions import AssertionEngine
from ..core.json_utils import JSONUtils, LargeJSONHandler


class APIExecutor:
    """Executes API requests with response chaining and variable substitution."""
    
    def __init__(self, timeout: int = 30, verify_ssl: bool = True, max_json_size_mb: int = 50):
        self.session = requests.Session()
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.variables: Dict[str, Any] = {}
        self.step_results: Dict[str, APIResponse] = {}
        self.assertion_engine = AssertionEngine()
        self.json_handler = LargeJSONHandler(max_json_size_mb)
        
    def execute_test_case(self, test_case: TestCase) -> TestResult:
        """Execute a complete test case."""
        start_time = datetime.now()
        
        result = TestResult(
            test_name=test_case.name,
            status=TestStatus.RUNNING,
            steps=[],
            start_time=start_time,
            variables={}
        )
        
        try:
            # Execute setup steps
            for step in test_case.setup:
                self._execute_step(step, result)
            
            # Execute main test steps
            for step in test_case.steps:
                self._execute_step(step, result)
            
            # Execute teardown steps
            for step in test_case.teardown:
                try:
                    self._execute_step(step, result)
                except Exception as e:
                    # Don't fail the test for teardown errors
                    result.steps.append({
                        'name': step.name,
                        'status': 'failed',
                        'error': str(e),
                        'step_type': 'teardown'
                    })
            
            result.status = TestStatus.PASSED
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
        
        finally:
            result.end_time = datetime.now()
            result.variables = self.variables.copy()
        
        return result
    
    def _execute_step(self, step: TestStep, result: TestResult):
        """Execute a single test step."""
        step_start = time.time()
        
        try:
            # Check dependencies
            self._check_dependencies(step)
            
            # Substitute variables in request
            request = self._substitute_variables(step.request)
            
            # Execute the API request
            response = self._make_request(request)
            
            # Store response for chaining
            self.step_results[step.name] = response
            
            # Validate response
            self._validate_response(step, response)
            
            # Extract variables
            self._extract_step_variables(step, response)
            
            step_result = {
                'name': step.name,
                'status': 'passed',
                'request': {
                    'method': request.method.value,
                    'url': request.url,
                    'headers': request.headers,
                    'body': request.body
                },
                'response': {
                    'status_code': response.status_code,
                    'headers': response.headers,
                    'body': response.body,
                    'response_time': response.response_time
                },
                'execution_time': time.time() - step_start
            }
            
            result.steps.append(step_result)
            
        except Exception as e:
            step_result = {
                'name': step.name,
                'status': 'failed',
                'error': str(e),
                'execution_time': time.time() - step_start
            }
            result.steps.append(step_result)
            raise
    
    def _check_dependencies(self, step: TestStep):
        """Check if step dependencies are satisfied."""
        for dep in step.depends_on:
            if dep not in self.step_results:
                raise ValueError(f"Step '{step.name}' depends on '{dep}' which has not been executed")
    
    def _substitute_variables(self, request: APIRequest) -> APIRequest:
        """Substitute variables in request components."""
        # Substitute in URL
        url = self._substitute_in_string(request.url)
        
        # Substitute in headers
        headers = {}
        for key, value in request.headers.items():
            headers[key] = self._substitute_in_string(value)
        
        # Substitute in parameters
        params = {}
        for key, value in request.params.items():
            params[key] = self._substitute_in_string(value)
        
        # Substitute in body
        body = None
        if request.body:
            if isinstance(request.body, str):
                body = self._substitute_in_string(request.body)
            elif isinstance(request.body, dict):
                body = self._substitute_in_dict(request.body)
        
        return APIRequest(
            method=request.method,
            url=url,
            headers=headers,
            params=params,
            body=body,
            auth=request.auth,
            timeout=request.timeout,
            name=request.name
        )
    
    def _substitute_in_string(self, text: str) -> str:
        """Substitute variables in a string."""
        if not isinstance(text, str):
            return text
        
        # Pattern for {{variable}} substitution
        pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'
        
        def replace_var(match):
            var_path = match.group(1)
            return str(self._get_variable_value(var_path))
        
        return re.sub(pattern, replace_var, text)
    
    def _substitute_in_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively substitute variables in a dictionary."""
        result = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._substitute_in_string(value)
            elif isinstance(value, dict):
                result[key] = self._substitute_in_dict(value)
            elif isinstance(value, list):
                result[key] = [self._substitute_in_string(item) if isinstance(item, str) else item for item in value]
            else:
                result[key] = value
        
        return result
    
    def _get_variable_value(self, var_path: str) -> Any:
        """Get variable value by path (e.g., 'user.id' or 'response.data.token')."""
        parts = var_path.split('.')
        
        # Check if it's a response reference
        if parts[0] in self.step_results:
            response = self.step_results[parts[0]]
            if len(parts) == 1:
                return response.body
            else:
                return self._get_nested_value(response.body, parts[1:])
        
        # Check regular variables
        if parts[0] in self.variables:
            value = self.variables[parts[0]]
            if len(parts) == 1:
                return value
            else:
                return self._get_nested_value(value, parts[1:])
        
        raise ValueError(f"Variable '{var_path}' not found")
    
    def _get_nested_value(self, data: Any, path_parts: List[str]) -> Any:
        """Get nested value from data structure."""
        current = data
        
        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    raise IndexError(f"Index {index} out of range")
            else:
                raise ValueError(f"Path '{'.'.join(path_parts)}' not found in data")
        
        return current
    
    def _make_request(self, request: APIRequest) -> APIResponse:
        """Make the actual HTTP request."""
        start_time = time.time()
        
        # Prepare request arguments
        kwargs = {
            'timeout': request.timeout,
            'verify': self.verify_ssl
        }
        
        if request.headers:
            kwargs['headers'] = request.headers
        
        if request.params:
            kwargs['params'] = request.params
        
        if request.body is not None:
            if isinstance(request.body, dict):
                kwargs['json'] = request.body
            else:
                kwargs['data'] = request.body
        
        if request.auth:
            if 'bearer' in request.auth:
                kwargs['headers'] = kwargs.get('headers', {})
                kwargs['headers']['Authorization'] = f"Bearer {request.auth['bearer']}"
            elif 'basic' in request.auth:
                kwargs['auth'] = (request.auth['basic']['username'], request.auth['basic']['password'])
        
        # Make the request
        response = self.session.request(
            method=request.method.value,
            url=request.url,
            **kwargs
        )
        
        # Parse response body
        try:
            body = response.json()
        except:
            body = response.text
        
        return APIResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            response_time=time.time() - start_time,
            request=request
        )
    
    def _validate_response(self, step: TestStep, response: APIResponse):
        """Validate response against step expectations."""
        
        # Check status code
        if response.status_code != step.expected_status:
            raise AssertionError(
                f"Expected status code {step.expected_status}, got {response.status_code}"
            )
        
        # Run advanced assertions (filter out status code validations)
        assertion_results = []
        for validation in step.validations:
            try:
                # Skip status code validations as they're handled above
                if validation.startswith('status code'):
                    continue
                    
                # Check if this is a legacy validation or new assertion format
                if self._is_legacy_validation(validation):
                    self._run_legacy_validation(validation, response)
                else:
                    # Use the new assertion engine
                    result = self.assertion_engine.evaluate_assertion(validation, response.body)
                    assertion_results.append(result)
                    
                    if not result['passed']:
                        raise AssertionError(result['message'])
                        
            except Exception as e:
                raise AssertionError(f"Validation failed: {validation} - {str(e)}")
        
        return assertion_results
    
    def _is_legacy_validation(self, validation: str) -> bool:
        """Check if validation uses legacy format."""
        legacy_patterns = [
            'response should contain',
            'response should not contain',
            'status code should be',
            'should be',
            'should not be'
        ]
        
        return any(pattern in validation.lower() for pattern in legacy_patterns)
    
    def _run_legacy_validation(self, validation: str, response: APIResponse):
        """Run legacy validation for backward compatibility."""
        
        # Status code validation
        if validation.startswith('status code should be'):
            expected = int(validation.split()[-1])
            if response.status_code != expected:
                raise AssertionError(f"Status code validation failed: expected {expected}, got {response.status_code}")
        
        # Content validation
        elif validation.startswith('response should contain'):
            content = validation.replace('response should contain', '').strip()
            content_str = json.dumps(response.body)
            if content not in content_str:
                raise AssertionError(f"Response should contain '{content}' but it doesn't")
        
        elif validation.startswith('response should not contain'):
            content = validation.replace('response should not contain', '').strip()
            content_str = json.dumps(response.body)
            if content in content_str:
                raise AssertionError(f"Response should not contain '{content}' but it does")
        
        # Field validation
        elif ' should be ' in validation:
            parts = validation.split(' should be ')
            field_path = parts[0].strip()
            expected_value = parts[1].strip()
            
            try:
                actual_value = JSONUtils.extract_nested_value(response.body, field_path.split('.'))
                if str(actual_value) != expected_value:
                    raise AssertionError(f"Field '{field_path}' should be '{expected_value}' but is '{actual_value}'")
            except (ValueError, KeyError):
                raise AssertionError(f"Field '{field_path}' not found in response")
        
        elif ' should not be ' in validation:
            parts = validation.split(' should not be ')
            field_path = parts[0].strip()
            expected_value = parts[1].strip()
            
            try:
                actual_value = JSONUtils.extract_nested_value(response.body, field_path.split('.'))
                if str(actual_value) == expected_value:
                    raise AssertionError(f"Field '{field_path}' should not be '{expected_value}' but it is")
            except (ValueError, KeyError):
                # Field not found, which is fine for "should not be"
                pass
    
    def _run_validation(self, validation: str, response: APIResponse):
        """Run a single validation rule."""
        # Status code validation
        if validation.startswith('status code should be'):
            expected = int(validation.split()[-1])
            if response.status_code != expected:
                raise AssertionError(f"Status code validation failed: expected {expected}, got {response.status_code}")
        
        # Content validation
        elif validation.startswith('response should contain'):
            content = validation.replace('response should contain', '').strip()
            content_str = json.dumps(response.body)
            if content not in content_str:
                raise AssertionError(f"Response should contain '{content}' but it doesn't")
        
        elif validation.startswith('response should not contain'):
            content = validation.replace('response should not contain', '').strip()
            content_str = json.dumps(response.body)
            if content in content_str:
                raise AssertionError(f"Response should not contain '{content}' but it does")
        
        # Field validation
        elif ' should be ' in validation:
            parts = validation.split(' should be ')
            field_path = parts[0].strip()
            expected_value = parts[1].strip()
            
            try:
                actual_value = self._get_nested_value(response.body, field_path.split('.'))
                if str(actual_value) != expected_value:
                    raise AssertionError(f"Field '{field_path}' should be '{expected_value}' but is '{actual_value}'")
            except (ValueError, KeyError):
                raise AssertionError(f"Field '{field_path}' not found in response")
        
        elif ' should not be ' in validation:
            parts = validation.split(' should not be ')
            field_path = parts[0].strip()
            expected_value = parts[1].strip()
            
            try:
                actual_value = self._get_nested_value(response.body, field_path.split('.'))
                if str(actual_value) == expected_value:
                    raise AssertionError(f"Field '{field_path}' should not be '{expected_value}' but it is")
            except (ValueError, KeyError):
                # Field not found, which is fine for "should not be"
                pass
    
    def _extract_step_variables(self, step: TestStep, response: APIResponse):
        """Extract variables from response for use in subsequent steps."""
        for var_name, path in step.extract_variables.items():
            try:
                # Use JSONUtils for advanced path extraction
                if '.' in path or '[' in path:
                    value = JSONUtils.extract_nested_value(response.body, path)
                else:
                    if isinstance(response.body, dict) and path in response.body:
                        value = response.body[path]
                    else:
                        value = response.body
                
                # Handle large JSON values
                if isinstance(value, (dict, list)):
                    json_size = JSONUtils.get_json_size(value)
                    if json_size['byte_size'] > self.json_handler.max_size_bytes:
                        # Store metadata for large JSON instead of full content
                        value = {
                            '_large_json_metadata': json_size,
                            '_truncated': True,
                            '_original_type': type(value).__name__
                        }
                
                self.variables[var_name] = value
                
            except Exception as e:
                raise ValueError(f"Failed to extract variable '{var_name}' from path '{path}': {str(e)}")
    
    def reset_variables(self):
        """Reset all variables and step results."""
        self.variables.clear()
        self.step_results.clear()
    
    def set_variable(self, name: str, value: Any):
        """Set a variable value."""
        self.variables[name] = value
    
    def get_variable(self, name: str) -> Any:
        """Get a variable value."""
        return self.variables.get(name)
