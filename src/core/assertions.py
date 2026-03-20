import json
import re
from typing import Any, Dict, List, Union, Optional
from datetime import datetime
import operator


class AssertionEngine:
    """Advanced assertion engine for API response validation."""
    
    def __init__(self):
        self.operators = {
            'equals': operator.eq,
            'not_equals': operator.ne,
            'greater_than': operator.gt,
            'less_than': operator.lt,
            'greater_equal': operator.ge,
            'less_equal': operator.le,
            'contains': self._contains,
            'not_contains': self._not_contains,
            'matches': self._matches,
            'not_matches': self._not_matches,
            'is_empty': self._is_empty,
            'is_not_empty': self._is_not_empty,
            'is_null': self._is_null,
            'is_not_null': self._is_not_null,
            'is_true': self._is_true,
            'is_false': self._is_false,
            'array_length': self._array_length,
            'array_contains': self._array_contains,
            'array_not_contains': self._array_not_contains,
            'object_has_key': self._object_has_key,
            'object_not_has_key': self._object_not_has_key,
            'type_is': self._type_is,
            'within_range': self._within_range,
            'is_valid_json': self._is_valid_json,
            'is_valid_email': self._is_valid_email,
            'is_valid_url': self._is_valid_url,
            'is_valid_ip': self._is_valid_ip,
            'date_format': self._date_format,
            'is_past_date': self._is_past_date,
            'is_future_date': self._is_future_date,
        }
    
    def evaluate_assertion(self, assertion: str, response_data: Any) -> Dict[str, Any]:
        """Evaluate a single assertion against response data."""
        
        try:
            # Parse the assertion
            parsed = self._parse_assertion(assertion)
            
            # Extract the actual value from response data
            actual_value = self._extract_value(response_data, parsed['path'])
            
            # Evaluate the assertion
            result = self._evaluate_condition(
                actual_value, 
                parsed['operator'], 
                parsed['expected_value'],
                parsed['options']
            )
            
            return {
                'assertion': assertion,
                'path': parsed['path'],
                'operator': parsed['operator'],
                'expected': parsed['expected_value'],
                'actual': actual_value,
                'passed': result,
                'message': self._generate_message(parsed, actual_value, result)
            }
            
        except Exception as e:
            return {
                'assertion': assertion,
                'passed': False,
                'error': str(e),
                'message': f"Assertion failed to evaluate: {str(e)}"
            }
    
    def _parse_assertion(self, assertion: str) -> Dict[str, Any]:
        """Parse assertion string into components."""
        
        # Pattern: path operator expected_value [options]
        # Examples:
        # "user.id equals 123"
        # "response.data.items array_length greater_than 0"
        # "response.email matches ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        # "response.timestamp is_past_date"
        
        # Handle special assertions without explicit paths
        if assertion.startswith('status code'):
            parts = assertion.split()
            if len(parts) >= 4 and parts[2] == 'should' and parts[3] == 'be':
                return {
                    'path': 'status_code',
                    'operator': 'equals',
                    'expected_value': parts[4],
                    'options': {}
                }
            else:
                return {
                    'path': 'status_code',
                    'operator': 'equals',
                    'expected_value': parts[-1],
                    'options': {}
                }
        
        # Parse complex assertions
        parts = assertion.split()
        
        if len(parts) < 3:
            raise ValueError(f"Invalid assertion format: {assertion}")
        
        # Find the operator (it could be multi-word like 'array_length')
        operator = None
        operator_index = None
        
        for op in self.operators.keys():
            op_parts = op.split('_')
            for i in range(len(parts) - len(op_parts) + 1):
                if ' '.join(parts[i:i+len(op_parts)]).replace('_', ' ') == op.replace('_', ' '):
                    operator = op
                    operator_index = i
                    break
            if operator:
                break
        
        if not operator:
            # Default to 'equals' if no operator found
            operator = 'equals'
            operator_index = 1
        
        # Extract path and expected value
        path = ' '.join(parts[:operator_index])
        expected_parts = parts[operator_index + len(operator.split('_')):]
        
        # Handle expected values with spaces (like regex patterns)
        expected_value = ' '.join(expected_parts) if expected_parts else None
        
        # Parse options (like case_sensitive: false)
        options = {}
        if ':' in expected_value:
            value_part, option_part = expected_value.rsplit(':', 1)
            expected_value = value_part.strip()
            try:
                options = json.loads('{' + option_part + '}')
            except:
                pass
        
        return {
            'path': path,
            'operator': operator,
            'expected_value': expected_value,
            'options': options
        }
    
    def _extract_value(self, data: Any, path: str) -> Any:
        """Extract value from data using JSON path."""
        
        if path == 'status_code':
            return data.get('status_code') if isinstance(data, dict) else data
        
        if not path:
            return data
        
        # Handle JSON path notation
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    raise ValueError(f"Path '{path}' not found in response data")
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    raise ValueError(f"Invalid array index '{part}' in path '{path}'")
            else:
                raise ValueError(f"Cannot navigate to '{part}' from non-indexable value")
        
        return current
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any, options: Dict[str, Any]) -> bool:
        """Evaluate the condition using the specified operator."""
        
        if operator not in self.operators:
            raise ValueError(f"Unknown operator: {operator}")
        
        return self.operators[operator](actual, expected, options)
    
    def _generate_message(self, parsed: Dict[str, Any], actual: Any, passed: bool) -> str:
        """Generate a descriptive assertion message."""
        
        if passed:
            return f"✓ {parsed['path']} {parsed['operator']} {parsed['expected_value']}"
        else:
            return f"✗ {parsed['path']} {parsed['operator']} {parsed['expected_value']} (actual: {actual})"
    
    # Operator implementations
    def _contains(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual contains expected."""
        if isinstance(actual, (str, list)):
            case_sensitive = options.get('case_sensitive', True)
            if not case_sensitive and isinstance(actual, str) and isinstance(expected, str):
                return expected.lower() in actual.lower()
            return expected in actual
        return False
    
    def _not_contains(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual does not contain expected."""
        return not self._contains(actual, expected, options)
    
    def _matches(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual matches regex pattern."""
        if isinstance(actual, str) and isinstance(expected, str):
            flags = 0
            if not options.get('case_sensitive', True):
                flags = re.IGNORECASE
            return bool(re.match(expected, actual, flags))
        return False
    
    def _not_matches(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual does not match regex pattern."""
        return not self._matches(actual, expected, options)
    
    def _is_empty(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is empty."""
        if actual is None:
            return True
        if isinstance(actual, (str, list, dict)):
            return len(actual) == 0
        return False
    
    def _is_not_empty(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is not empty."""
        return not self._is_empty(actual, expected, options)
    
    def _is_null(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is null."""
        return actual is None
    
    def _is_not_null(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is not null."""
        return actual is not None
    
    def _is_true(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is truthy."""
        return bool(actual)
    
    def _is_false(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is falsy."""
        return not bool(actual)
    
    def _array_length(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check array length condition."""
        if not isinstance(actual, list):
            return False
        
        length = len(actual)
        
        # Parse expected condition
        if isinstance(expected, str) and ' ' in expected:
            parts = expected.split()
            if len(parts) == 2:
                op, value = parts
                try:
                    value = int(value)
                    if op == 'greater_than':
                        return length > value
                    elif op == 'less_than':
                        return length < value
                    elif op == 'equals':
                        return length == value
                    elif op == 'greater_equal':
                        return length >= value
                    elif op == 'less_equal':
                        return length <= value
                except ValueError:
                    pass
        
        return length == int(expected) if isinstance(expected, str) else length == expected
    
    def _array_contains(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if array contains expected value."""
        return isinstance(actual, list) and expected in actual
    
    def _array_not_contains(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if array does not contain expected value."""
        return not self._array_contains(actual, expected, options)
    
    def _object_has_key(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if object has expected key."""
        return isinstance(actual, dict) and expected in actual
    
    def _object_not_has_key(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if object does not have expected key."""
        return not self._object_has_key(actual, expected, options)
    
    def _type_is(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is of expected type."""
        type_map = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }
        
        expected_type = type_map.get(expected.lower())
        if expected_type:
            return isinstance(actual, expected_type)
        
        return type(actual).__name__ == expected
    
    def _within_range(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual value is within expected range."""
        if isinstance(expected, str) and '-' in expected:
            try:
                min_val, max_val = map(float, expected.split('-'))
                return min_val <= float(actual) <= max_val
            except (ValueError, TypeError):
                pass
        return False
    
    def _is_valid_json(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is valid JSON."""
        if isinstance(actual, str):
            try:
                json.loads(actual)
                return True
            except json.JSONDecodeError:
                return False
        return isinstance(actual, (dict, list))
    
    def _is_valid_email(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is valid email."""
        if not isinstance(actual, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, actual))
    
    def _is_valid_url(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is valid URL."""
        if not isinstance(actual, str):
            return False
        
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        return bool(re.match(pattern, actual))
    
    def _is_valid_ip(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual is valid IP address."""
        if not isinstance(actual, str):
            return False
        
        import ipaddress
        try:
            ipaddress.ip_address(actual)
            return True
        except ValueError:
            return False
    
    def _date_format(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual matches expected date format."""
        if not isinstance(actual, str):
            return False
        
        try:
            from datetime import datetime
            datetime.strptime(actual, expected)
            return True
        except ValueError:
            return False
    
    def _is_past_date(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual date is in the past."""
        try:
            if isinstance(actual, str):
                from datetime import datetime
                date_obj = datetime.fromisoformat(actual.replace('Z', '+00:00'))
                return date_obj < datetime.now()
            return False
        except (ValueError, TypeError):
            return False
    
    def _is_future_date(self, actual: Any, expected: Any, options: Dict[str, Any]) -> bool:
        """Check if actual date is in the future."""
        try:
            if isinstance(actual, str):
                from datetime import datetime
                date_obj = datetime.fromisoformat(actual.replace('Z', '+00:00'))
                return date_obj > datetime.now()
            return False
        except (ValueError, TypeError):
            return False


class AssertionBuilder:
    """Builder for creating complex assertions."""
    
    @staticmethod
    def field_equals(path: str, value: Any) -> str:
        """Create field equals assertion."""
        return f"{path} equals {value}"
    
    @staticmethod
    def field_contains(path: str, value: Any) -> str:
        """Create field contains assertion."""
        return f"{path} contains {value}"
    
    @staticmethod
    def field_matches(path: str, pattern: str) -> str:
        """Create field matches regex assertion."""
        return f"{path} matches {pattern}"
    
    @staticmethod
    def array_length_greater_than(path: str, length: int) -> str:
        """Create array length greater than assertion."""
        return f"{path} array_length greater_than {length}"
    
    @staticmethod
    def array_length_equals(path: str, length: int) -> str:
        """Create array length equals assertion."""
        return f"{path} array_length equals {length}"
    
    @staticmethod
    def field_type_is(path: str, expected_type: str) -> str:
        """Create field type assertion."""
        return f"{path} type_is {expected_type}"
    
    @staticmethod
    def field_within_range(path: str, min_val: float, max_val: float) -> str:
        """Create field within range assertion."""
        return f"{path} within_range {min_val}-{max_val}"
    
    @staticmethod
    def field_is_valid_email(path: str) -> str:
        """Create valid email assertion."""
        return f"{path} is_valid_email"
    
    @staticmethod
    def field_is_valid_url(path: str) -> str:
        """Create valid URL assertion."""
        return f"{path} is_valid_url"
    
    @staticmethod
    def field_is_past_date(path: str) -> str:
        """Create past date assertion."""
        return f"{path} is_past_date"
    
    @staticmethod
    def field_is_future_date(path: str) -> str:
        """Create future date assertion."""
        return f"{path} is_future_date"
