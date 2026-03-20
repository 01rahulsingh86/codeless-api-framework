import json
import yaml
from typing import Any, Dict, List, Union, Optional
from pathlib import Path
import jsonschema
from jsonschema import validate, ValidationError


class JSONUtils:
    """Utilities for handling large and complex JSON structures."""
    
    @staticmethod
    def load_json_from_file(file_path: str) -> Any:
        """Load JSON from file with error handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {file_path}: {str(e)}")
    
    @staticmethod
    def load_yaml_as_json(file_path: str) -> Any:
        """Load YAML file and convert to JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAML file not found: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in file {file_path}: {str(e)}")
    
    @staticmethod
    def extract_nested_value(data: Any, path: str) -> Any:
        """Extract nested value using JSON path notation."""
        
        if not path:
            return data
        
        # Handle array notation with brackets
        if '[' in path and ']' in path:
            return JSONUtils._extract_with_brackets(data, path)
        
        # Handle dot notation
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    raise KeyError(f"Key '{part}' not found in path '{path}'")
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    raise IndexError(f"Invalid array index '{part}' in path '{path}'")
            else:
                raise TypeError(f"Cannot navigate to '{part}' from {type(current).__name__}")
        
        return current
    
    @staticmethod
    def _extract_with_brackets(data: Any, path: str) -> Any:
        """Extract value using bracket notation for arrays."""
        # Split on dots first, then handle brackets
        parts = path.split('.')
        current = data
        
        for part in parts:
            if '[' in part and ']' in part:
                # Handle array access like "items[0].name"
                base_part = part.split('[')[0]
                array_part = part.split('[')[1].split(']')[0]
                
                # Navigate to base
                if base_part:
                    if isinstance(current, dict) and base_part in current:
                        current = current[base_part]
                    else:
                        raise KeyError(f"Key '{base_part}' not found")
                
                # Handle array index
                if isinstance(current, list):
                    try:
                        current = current[int(array_part)]
                    except (ValueError, IndexError):
                        raise IndexError(f"Invalid array index '{array_part}'")
                else:
                    raise TypeError(f"Cannot index non-array type")
                
                # Handle remaining part after brackets
                remaining = part.split(']')[1:]
                if remaining:
                    remaining_path = '.'.join(remaining).lstrip('.')
                    if remaining_path:
                        current = JSONUtils.extract_nested_value(current, remaining_path)
            else:
                # Regular dot notation
                if isinstance(current, dict):
                    if part in current:
                        current = current[part]
                    else:
                        raise KeyError(f"Key '{part}' not found")
                elif isinstance(current, list):
                    try:
                        current = current[int(part)]
                    except (ValueError, IndexError):
                        raise IndexError(f"Invalid array index '{part}'")
                else:
                    raise TypeError(f"Cannot navigate to '{part}' from {type(current).__name__}")
        
        return current
    
    @staticmethod
    def flatten_json(data: Any, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested JSON into dot-separated keys."""
        
        items = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key
                items.extend(JSONUtils.flatten_json(value, new_key, sep).items())
        elif isinstance(data, list):
            for i, value in enumerate(data):
                new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
                items.extend(JSONUtils.flatten_json(value, new_key, sep).items())
        else:
            return {parent_key: data}
        
        return dict(items)
    
    @staticmethod
    def search_json(data: Any, search_term: str, case_sensitive: bool = True) -> List[Dict[str, Any]]:
        """Search for values in JSON structure."""
        
        results = []
        
        if not case_sensitive:
            search_term = search_term.lower()
        
        def _search_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    
                    # Check key
                    key_match = (search_term in key) if case_sensitive else (search_term in key.lower())
                    if key_match:
                        results.append({
                            'path': new_path,
                            'type': 'key',
                            'value': key,
                            'parent_path': path
                        })
                    
                    # Recursively search value
                    _search_recursive(value, new_path)
                    
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    _search_recursive(value, new_path)
            
            else:
                # Check value
                value_str = str(obj)
                value_match = (search_term in value_str) if case_sensitive else (search_term in value_str.lower())
                if value_match:
                    results.append({
                        'path': path,
                        'type': 'value',
                        'value': obj,
                        'parent_path': path.rsplit('.', 1)[0] if '.' in path else ''
                    })
        
        _search_recursive(data)
        return results
    
    @staticmethod
    def validate_json_schema(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON against a schema."""
        
        try:
            validate(instance=data, schema=schema)
            return {
                'valid': True,
                'errors': []
            }
        except ValidationError as e:
            return {
                'valid': False,
                'errors': [{
                    'path': '.'.join(str(p) for p in e.path) if e.path else 'root',
                    'message': e.message,
                    'failed_value': e.instance,
                    'schema_path': '.'.join(str(p) for p in e.schema_path) if e.schema_path else 'root'
                }]
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [{
                    'message': f"Schema validation error: {str(e)}"
                }]
            }
    
    @staticmethod
    def merge_json(*json_objects: Any) -> Any:
        """Merge multiple JSON objects."""
        
        result = {}
        
        for obj in json_objects:
            if isinstance(obj, dict):
                result.update(obj)
            else:
                raise TypeError("Can only merge dictionary objects")
        
        return result
    
    @staticmethod
    def compare_json(obj1: Any, obj2: Any, ignore_keys: List[str] = None) -> Dict[str, Any]:
        """Compare two JSON objects and return differences."""
        
        ignore_keys = ignore_keys or []
        
        def _remove_ignored(obj, path=""):
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if current_path not in ignore_keys and key not in ignore_keys:
                        result[key] = _remove_ignored(value, current_path)
                return result
            elif isinstance(obj, list):
                return [_remove_ignored(item, f"{path}[{i}]") for i, item in enumerate(obj)]
            else:
                return obj
        
        cleaned_obj1 = _remove_ignored(obj1)
        cleaned_obj2 = _remove_ignored(obj2)
        
        differences = []
        
        def _find_diffs(o1, o2, path=""):
            if type(o1) != type(o2):
                differences.append({
                    'path': path,
                    'type': 'type_mismatch',
                    'obj1': o1,
                    'obj2': o2
                })
            elif isinstance(o1, dict):
                all_keys = set(o1.keys()) | set(o2.keys())
                for key in all_keys:
                    current_path = f"{path}.{key}" if path else key
                    if key not in o1:
                        differences.append({
                            'path': current_path,
                            'type': 'missing_in_obj1',
                            'obj2': o2[key]
                        })
                    elif key not in o2:
                        differences.append({
                            'path': current_path,
                            'type': 'missing_in_obj2',
                            'obj1': o1[key]
                        })
                    else:
                        _find_diffs(o1[key], o2[key], current_path)
            elif isinstance(o1, list):
                if len(o1) != len(o2):
                    differences.append({
                        'path': path,
                        'type': 'array_length_mismatch',
                        'obj1_length': len(o1),
                        'obj2_length': len(o2)
                    })
                else:
                    for i, (item1, item2) in enumerate(zip(o1, o2)):
                        _find_diffs(item1, item2, f"{path}[{i}]")
            elif o1 != o2:
                differences.append({
                    'path': path,
                    'type': 'value_mismatch',
                    'obj1': o1,
                    'obj2': o2
                })
        
        _find_diffs(cleaned_obj1, cleaned_obj2)
        
        return {
            'equal': len(differences) == 0,
            'differences': differences
        }
    
    @staticmethod
    def pretty_print_json(data: Any, indent: int = 2) -> str:
        """Pretty print JSON with proper formatting."""
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    
    @staticmethod
    def truncate_json(data: Any, max_length: int = 1000) -> str:
        """Truncate JSON string for display purposes."""
        json_str = JSONUtils.pretty_print_json(data)
        if len(json_str) <= max_length:
            return json_str
        
        truncated = json_str[:max_length]
        return truncated + "... (truncated)"
    
    @staticmethod
    def get_json_size(data: Any) -> Dict[str, int]:
        """Get size information about JSON data."""
        
        def _count_items(obj):
            if isinstance(obj, dict):
                return len(obj) + sum(_count_items(v) for v in obj.values())
            elif isinstance(obj, list):
                return len(obj) + sum(_count_items(item) for item in obj)
            else:
                return 1
        
        json_str = json.dumps(data, ensure_ascii=False)
        
        return {
            'character_count': len(json_str),
            'byte_size': len(json_str.encode('utf-8')),
            'total_items': _count_items(data),
            'max_depth': JSONUtils._get_max_depth(data)
        }
    
    @staticmethod
    def _get_max_depth(obj, current_depth=0):
        """Calculate maximum depth of nested JSON."""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(JSONUtils._get_max_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(JSONUtils._get_max_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth


class LargeJSONHandler:
    """Handler for large JSON payloads with memory optimization."""
    
    def __init__(self, max_size_mb: int = 50):
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def process_large_json(self, data: Any, processor_func) -> Any:
        """Process large JSON with memory management."""
        
        json_size = len(json.dumps(data).encode('utf-8'))
        
        if json_size > self.max_size_bytes:
            return self._process_in_chunks(data, processor_func)
        else:
            return processor_func(data)
    
    def _process_in_chunks(self, data: Any, processor_func) -> Any:
        """Process large JSON in chunks to save memory."""
        
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = self.process_large_json(value, processor_func)
            return result
        elif isinstance(data, list):
            result = []
            for item in data:
                result.append(self.process_large_json(item, processor_func))
            return result
        else:
            return processor_func(data)
    
    def stream_json_file(self, file_path: str, chunk_size: int = 8192):
        """Stream large JSON file in chunks."""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            buffer = ""
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                buffer += chunk
                
                # Process complete JSON objects in buffer
                while True:
                    try:
                        obj, idx = json.JSONDecoder().raw_decode(buffer)
                        yield obj
                        buffer = buffer[idx:].lstrip()
                    except json.JSONDecodeError:
                        break
