import re
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..core.models import (
    TestCase, TestStep, APIRequest, HttpMethod, 
    TestSuite
)


class NLParser:
    """Parses natural language test definitions into structured test cases."""
    
    def __init__(self):
        self.variable_pattern = r'\{\{(\w+)\}\}'
        self.extraction_pattern = r'extract\s+(\w+)\s+from\s+(.+)'
        self.validation_patterns = [
            r'status\s+code\s+should\s+be\s+(\d+)',
            r'response\s+should\s+contain\s+(.+)',
            r'response\s+should\s+not\s+contain\s+(.+)',
            r'(\w+)\s+should\s+be\s+(.+)',
            r'(\w+)\s+should\s+not\s+be\s+(.+)'
        ]
        
    def parse_file(self, file_path: str) -> TestSuite:
        """Parse a test file and return a TestSuite."""
        path = Path(file_path)
        
        if path.suffix.lower() in ['.yml', '.yaml']:
            return self._parse_yaml_file(path)
        elif path.suffix.lower() == '.txt':
            return self._parse_text_file(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def _parse_yaml_file(self, path: Path) -> TestSuite:
        """Parse YAML-based test definition."""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return self._parse_test_suite_data(data, path.stem)
    
    def _parse_text_file(self, path: Path) -> TestSuite:
        """Parse natural language text file."""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self._parse_nl_content(content, path.stem)
    
    def _parse_test_suite_data(self, data: Dict[str, Any], name: str) -> TestSuite:
        """Parse test suite data from dictionary."""
        tests = []
        
        for test_data in data.get('tests', []):
            test = self._parse_test_data(test_data)
            tests.append(test)
        
        return TestSuite(
            name=name,
            tests=tests,
            config=data.get('config', {}),
            global_setup=self._parse_steps(data.get('global_setup', [])),
            global_teardown=self._parse_steps(data.get('global_teardown', []))
        )
    
    def _parse_test_data(self, test_data: Dict[str, Any]) -> TestCase:
        """Parse individual test data."""
        steps = self._parse_steps(test_data.get('steps', []))
        setup = self._parse_steps(test_data.get('setup', []))
        teardown = self._parse_steps(test_data.get('teardown', []))
        
        return TestCase(
            name=test_data['name'],
            description=test_data.get('description', ''),
            steps=steps,
            setup=setup,
            teardown=teardown,
            tags=test_data.get('tags', []),
            timeout=test_data.get('timeout', 300)
        )
    
    def _parse_steps(self, steps_data: List[Dict[str, Any]]) -> List[TestStep]:
        """Parse list of step data into TestStep objects."""
        steps = []
        
        for step_data in steps_data:
            if isinstance(step_data, str):
                # Natural language step
                step = self._parse_nl_step(step_data)
            else:
                # Structured step
                step = self._parse_structured_step(step_data)
            steps.append(step)
        
        return steps
    
    def _parse_nl_step(self, step_text: str) -> TestStep:
        """Parse a natural language step into TestStep."""
        step_text = step_text.strip()
        
        # Extract step name (first part before the action)
        name_match = re.match(r'^(.+?):\s*(.+)', step_text, re.DOTALL)
        if name_match:
            name = name_match.group(1).strip()
            action_text = name_match.group(2).strip()
        else:
            name = step_text[:50] + "..." if len(step_text) > 50 else step_text
            action_text = step_text
        
        # Parse HTTP method and URL
        method, url = self._extract_method_and_url(action_text)
        
        # Extract headers, body, params from the full step text (not just action_text)
        headers = self._extract_headers(step_text)
        body = self._extract_body(step_text)
        params = self._extract_params(step_text)
        
        # Extract validations
        expected_status, validations = self._extract_validations(step_text)
        
        # Extract variable assignments
        extract_vars = self._extract_variables(step_text)
        
        # Extract dependencies
        depends_on = self._extract_dependencies(step_text)
        
        request = APIRequest(
            method=method,
            url=url,
            headers=headers,
            params=params,
            body=body,
            name=name
        )
        
        return TestStep(
            name=name,
            request=request,
            expected_status=expected_status,
            validations=validations,
            extract_variables=extract_vars,
            depends_on=depends_on
        )
    
    def _parse_structured_step(self, step_data: Dict[str, Any]) -> TestStep:
        """Parse structured step data."""
        method = HttpMethod(step_data['method'].upper())
        url = step_data['url']
        
        request = APIRequest(
            method=method,
            url=url,
            headers=step_data.get('headers', {}),
            params=step_data.get('params', {}),
            body=step_data.get('body'),
            auth=step_data.get('auth'),
            timeout=step_data.get('timeout', 30),
            name=step_data.get('name')
        )
        
        return TestStep(
            name=step_data.get('name', f"{method} {url}"),
            request=request,
            expected_status=step_data.get('expected_status', 200),
            validations=step_data.get('validations', []),
            extract_variables=step_data.get('extract_variables', {}),
            depends_on=step_data.get('depends_on', [])
        )
    
    def _extract_method_and_url(self, text: str) -> tuple[HttpMethod, str]:
        """Extract HTTP method and URL from text."""
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        
        # Handle multi-line YAML-like format
        lines = text.split('\n')
        method = None
        url = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for method at the beginning of a line
            for m in methods:
                if line.startswith(m):
                    parts = line.split(None, 1)
                    if len(parts) >= 2:
                        method = HttpMethod(m.upper())
                        url = parts[1].strip()
                        return method, url
        
        # Fallback to original pattern matching
        for m in methods:
            pattern = rf'{m}\s+([^\s]+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return HttpMethod(m.upper()), match.group(1)
        
        # Default to GET if no method found
        url_match = re.search(r'https?://[^\s]+', text)
        if url_match:
            return HttpMethod.GET, url_match.group(0)
        
        raise ValueError("Could not extract HTTP method and URL from text")
    
    def _extract_headers(self, text: str) -> Dict[str, str]:
        """Extract headers from text."""
        headers = {}
        
        # Look for headers section after the method and URL
        lines = text.split('\n')
        in_headers_section = False
        
        for line in lines:
            line = line.strip()
            
            # Check if we're entering a headers section
            if line.lower().startswith('headers:') or line.lower().startswith('with headers'):
                in_headers_section = True
                continue
            
            # Check if we're leaving the headers section
            if in_headers_section and (line.lower().startswith('body:') or line.lower().startswith('status') or line.lower().startswith('extract')):
                in_headers_section = False
                continue
            
            # Extract headers if we're in the headers section
            if in_headers_section and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    header = parts[0].strip()
                    value = parts[1].strip()
                    if header and value:
                        headers[header] = value
        
        # Fallback patterns for inline headers
        if not headers:
            header_patterns = [
                r'headers?\s*:\s*\{([^}]+)\}',
                r'with\s+headers?\s*\{([^}]+)\}',
            ]
            
            for pattern in header_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        header_str = match.group(1)
                        # Parse simple header format like "Content-Type: application/json"
                        for header_line in header_str.split(','):
                            if ':' in header_line:
                                h, v = header_line.split(':', 1)
                                headers[h.strip()] = v.strip().strip('"\'')
                    except:
                        pass
        
        return headers
    
    def _extract_body(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract request body from text."""
        
        # Check for body file reference
        file_match = re.search(r'body\s+from\s+file\s+([^\s]+)', text, re.IGNORECASE)
        if file_match:
            file_path = file_match.group(1)
            return self._load_body_from_file(file_path)
        
        # Look for multi-line YAML-style body
        lines = text.split('\n')
        in_body_section = False
        body_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if we're entering a body section
            if line_stripped.lower().startswith('body:'):
                in_body_section = True
                continue
            
            # Check if we're leaving the body section
            if in_body_section and (line_stripped.lower().startswith('status') or line_stripped.lower().startswith('extract') or line_stripped.lower().startswith('response')):
                in_body_section = False
                continue
            
            # Collect body lines if we're in the body section
            if in_body_section:
                if line_stripped:  # Only add non-empty lines
                    body_lines.append(line_stripped)
        
        # Parse the collected body lines
        if body_lines:
            body_text = '\n'.join(body_lines)
            try:
                import json
                return json.loads(body_text)
            except json.JSONDecodeError:
                # Try to parse as YAML
                try:
                    import yaml
                    return yaml.safe_load(body_text)
                except:
                    pass
        
        # Fallback: Look for JSON-like content in the entire text
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested JSON
            r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # Arrays
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    import json
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _load_body_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load request body from external file."""
        from ..core.json_utils import JSONUtils
        
        try:
            if file_path.endswith('.json'):
                return JSONUtils.load_json_from_file(file_path)
            elif file_path.endswith(('.yml', '.yaml')):
                return JSONUtils.load_yaml_as_json(file_path)
            else:
                # Try to parse as JSON first, then as plain text
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
        except Exception as e:
            raise ValueError(f"Failed to load body from file {file_path}: {str(e)}")
    
    def _extract_params(self, text: str) -> Dict[str, Any]:
        """Extract query parameters from text."""
        params = {}
        
        # Pattern for "param=value" or "parameter param to value"
        param_patterns = [
            r'(\w+)\s*=\s*([^,\s]+)',
            r'parameter\s+(\w+)\s+to\s+([^,\s]+)',
            r'param\s+(\w+)\s*=\s*([^,\s]+)'
        ]
        
        for pattern in param_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for param, value in matches:
                params[param.strip()] = value.strip()
        
        return params
    
    def _extract_validations(self, text: str) -> tuple[int, List[str]]:
        """Extract expected status code and validations from text."""
        expected_status = 200
        validations = []
        
        # Check for status code expectations
        status_match = re.search(r'status\s+code\s+should\s+be\s+(\d+)', text, re.IGNORECASE)
        if status_match:
            expected_status = int(status_match.group(1))
        
        # Extract advanced assertions
        assertion_patterns = [
            r'([^\n]+?)\s+(equals|contains|not_contains|matches|not_matches|greater_than|less_than|greater_equal|less_equal|is_empty|is_not_empty|is_null|is_not_null|is_true|is_false|array_length|array_contains|array_not_contains|object_has_key|object_not_has_key|type_is|within_range|is_valid_json|is_valid_email|is_valid_url|date_format|is_past_date|is_future_date)\s+([^\n]+)',
        ]
        
        for pattern in assertion_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) == 3:
                    field_path, operator, expected_value = match
                    # Convert to assertion format
                    assertion = f"{field_path.strip()} {operator.replace(' ', '_')} {expected_value.strip()}"
                    validations.append(assertion)
        
        # Legacy validations for backward compatibility (excluding status code)
        legacy_patterns = [
            r'response\s+should\s+contain\s+(.+)',
            r'response\s+should\s+not\s+contain\s+(.+)',
            r'(\w+(?:\.\w+)*)\s+should\s+be\s+(.+)',
            r'(\w+(?:\.\w+)*)\s+should\s+not\s+be\s+(.+)'
        ]
        
        for pattern in legacy_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Skip status code validations as they're handled separately
                if isinstance(match, tuple) and len(match) == 2:
                    field_path, expected_value = match
                    if field_path.lower() in ['status', 'status_code', 'code']:
                        continue
                validations.append(match)
        
        return expected_status, validations
    
    def _extract_variables(self, text: str) -> Dict[str, str]:
        """Extract variable assignments from text."""
        variables = {}
        
        matches = re.findall(self.extraction_pattern, text, re.IGNORECASE)
        for var_name, path in matches:
            variables[var_name.strip()] = path.strip()
        
        return variables
    
    def _extract_dependencies(self, text: str) -> List[str]:
        """Extract step dependencies from text."""
        dependencies = []
        
        # Look for "after step_name" or "depends on step_name"
        dep_patterns = [
            r'after\s+(\w+)',
            r'depends\s+on\s+(\w+)',
            r'use\s+response\s+from\s+(\w+)'
        ]
        
        for pattern in dep_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dependencies.extend(matches)
        
        return dependencies
    
    def _parse_nl_content(self, content: str, name: str) -> TestSuite:
        """Parse natural language content into TestSuite."""
        lines = content.split('\n')
        
        tests = []
        current_test = None
        current_steps = []
        current_step_lines = []
        in_step = False
        
        for line in lines:
            stripped_line = line.strip()
            
            if stripped_line.startswith('Test:'):
                # Save previous test if exists
                if current_test:
                    if current_step_lines:
                        # Parse the accumulated step
                        step_text = '\n'.join(current_step_lines)
                        step = self._parse_nl_step(step_text)
                        current_steps.append(step)
                        current_step_lines = []
                    
                    current_test.steps = current_steps
                    tests.append(current_test)
                
                # Start new test
                test_name = stripped_line[5:].strip()
                current_test = TestCase(
                    name=test_name,
                    description="",
                    steps=[]
                )
                current_steps = []
                in_step = False
            
            elif stripped_line.startswith('Description:'):
                if current_test:
                    current_test.description = stripped_line[12:].strip()
            
            elif stripped_line.startswith('-') or stripped_line.startswith('*'):
                # Save previous step if we were accumulating one
                if current_step_lines:
                    step_text = '\n'.join(current_step_lines)
                    step = self._parse_nl_step(step_text)
                    current_steps.append(step)
                    current_step_lines = []
                
                # Start new step
                current_step_lines = [stripped_line[1:].strip()]
                in_step = True
            
            elif in_step and stripped_line:
                # Continue accumulating step content (maintain indentation)
                current_step_lines.append(line.rstrip())
            elif in_step and not stripped_line:
                # Empty line ends the step
                if current_step_lines:
                    step_text = '\n'.join(current_step_lines)
                    step = self._parse_nl_step(step_text)
                    current_steps.append(step)
                    current_step_lines = []
                in_step = False
        
        # Save last step and test
        if current_step_lines:
            step_text = '\n'.join(current_step_lines)
            step = self._parse_nl_step(step_text)
            current_steps.append(step)
        
        if current_test:
            current_test.steps = current_steps
            tests.append(current_test)
        
        return TestSuite(name=name, tests=tests)
