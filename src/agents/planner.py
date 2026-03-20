import os
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from ..core.models import TestSuite
from ..parser import NLParser


@dataclass
class ExecutionPlan:
    """Represents a test execution plan."""
    test_files: List[str]
    execution_order: List[str]
    parallel_groups: List[List[str]]
    environment: Dict[str, Any]
    config: Dict[str, Any]
    dependencies: Dict[str, List[str]]


class TestPlanner:
    """Plans test execution strategy and dependencies."""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.parser = NLParser()
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            'test_directory': 'tests',
            'parallel_execution': True,
            'max_parallel_tests': 5,
            'timeout': 300,
            'retry_failed_tests': False,
            'retry_count': 2,
            'environment': {},
            'global_variables': {},
            'reporting': {
                'html': True,
                'json': True,
                'output_directory': 'reports'
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        
        return default_config
    
    def create_execution_plan(self, test_paths: List[str] = None, 
                            environment: str = 'default') -> ExecutionPlan:
        """Create an execution plan for the given test files."""
        
        # Discover test files if not provided
        if test_paths is None:
            test_paths = self._discover_test_files()
        
        # Parse all test files
        test_suites = {}
        for test_path in test_paths:
            try:
                suite = self.parser.parse_file(test_path)
                test_suites[test_path] = suite
            except Exception as e:
                print(f"Warning: Failed to parse {test_path}: {e}")
                continue
        
        # Analyze dependencies and create execution order
        execution_order, parallel_groups = self._analyze_dependencies(test_suites)
        
        # Load environment configuration
        env_config = self._load_environment_config(environment)
        
        return ExecutionPlan(
            test_files=list(test_suites.keys()),
            execution_order=execution_order,
            parallel_groups=parallel_groups,
            environment=env_config,
            config=self.config,
            dependencies=self._extract_dependencies(test_suites)
        )
    
    def _discover_test_files(self) -> List[str]:
        """Discover test files in the configured directory."""
        test_dir = Path(self.config['test_directory'])
        test_files = []
        
        # Look for .txt, .yml, .yaml files
        for ext in ['*.txt', '*.yml', '*.yaml']:
            test_files.extend(test_dir.glob(ext))
            test_files.extend(test_dir.glob(f'**/{ext}'))
        
        return [str(f) for f in test_files]
    
    def _analyze_dependencies(self, test_suites: Dict[str, TestSuite]) -> tuple[List[str], List[List[str]]]:
        """Analyze test dependencies and create execution order."""
        
        # Build dependency graph
        dependency_graph = {}
        for test_path, suite in test_suites.items():
            dependencies = set()
            
            # Check for cross-test dependencies (via tags or naming conventions)
            for test in suite.tests:
                for step in test.steps + test.setup + test.teardown:
                    # Look for dependencies in step names or descriptions
                    for dep in step.depends_on:
                        if '.' not in dep:  # Cross-test dependency
                            dependencies.add(dep)
            
            dependency_graph[test_path] = list(dependencies)
        
        # Topological sort for execution order
        execution_order = self._topological_sort(dependency_graph)
        
        # Group tests for parallel execution
        parallel_groups = []
        if self.config['parallel_execution']:
            parallel_groups = self._create_parallel_groups(execution_order, dependency_graph)
        else:
            parallel_groups = [[test] for test in execution_order]
        
        return execution_order, parallel_groups
    
    def _topological_sort(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph."""
        
        # Create in-degree count
        in_degree = {node: 0 for node in dependency_graph}
        for node in dependency_graph:
            for dep in dependency_graph[node]:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Queue of nodes with no dependencies
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Update in-degree for neighbors
            for neighbor in dependency_graph:
                if node in dependency_graph[neighbor]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        # Check for circular dependencies
        if len(result) != len(dependency_graph):
            raise ValueError("Circular dependency detected in test files")
        
        return result
    
    def _create_parallel_groups(self, execution_order: List[str], 
                             dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """Create groups of tests that can run in parallel."""
        
        groups = []
        current_group = []
        max_parallel = self.config['max_parallel_tests']
        
        for test_file in execution_order:
            # Check if this test can run with current group
            can_run_in_parallel = True
            
            for group_test in current_group:
                # Check if there's any dependency between tests
                if (test_file in dependency_graph.get(group_test, []) or
                    group_test in dependency_graph.get(test_file, [])):
                    can_run_in_parallel = False
                    break
            
            if not can_run_in_parallel or len(current_group) >= max_parallel:
                # Start new group
                if current_group:
                    groups.append(current_group)
                current_group = [test_file]
            else:
                current_group.append(test_file)
        
        # Add last group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _extract_dependencies(self, test_suites: Dict[str, TestSuite]) -> Dict[str, List[str]]:
        """Extract all dependencies from test suites."""
        dependencies = {}
        
        for test_path, suite in test_suites.items():
            test_deps = []
            
            for test in suite.tests:
                for step in test.steps + test.setup + test.teardown:
                    test_deps.extend(step.depends_on)
            
            dependencies[test_path] = list(set(test_deps))  # Remove duplicates
        
        return dependencies
    
    def _load_environment_config(self, environment: str) -> Dict[str, Any]:
        """Load environment-specific configuration."""
        
        # Base environment config
        env_config = {
            'name': environment,
            'variables': self.config.get('global_variables', {}).copy(),
            'timeout': self.config.get('timeout', 300),
            'retry_count': self.config.get('retry_count', 2)
        }
        
        # Try to load environment-specific file
        env_file = Path(f'config/environments/{environment}.yml')
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_specific = yaml.safe_load(f)
                env_config.update(env_specific)
        
        # Override with environment variables
        env_vars = self._get_environment_variables()
        env_config['variables'].update(env_vars)
        
        return env_config
    
    def _get_environment_variables(self) -> Dict[str, str]:
        """Get framework-specific environment variables."""
        env_vars = {}
        
        # Look for variables with API_TEST_ prefix
        for key, value in os.environ.items():
            if key.startswith('API_TEST_'):
                # Remove prefix and convert to lowercase
                var_name = key[9:].lower()
                env_vars[var_name] = value
        
        return env_vars
    
    def validate_plan(self, plan: ExecutionPlan) -> List[str]:
        """Validate execution plan and return list of issues."""
        issues = []
        
        # Check if test files exist
        for test_file in plan.test_files:
            if not Path(test_file).exists():
                issues.append(f"Test file not found: {test_file}")
        
        # Check for circular dependencies
        try:
            self._topological_sort(plan.dependencies)
        except ValueError as e:
            issues.append(f"Circular dependency detected: {e}")
        
        # Check environment configuration
        if not plan.environment:
            issues.append("No environment configuration provided")
        
        return issues
    
    def save_plan(self, plan: ExecutionPlan, output_path: str):
        """Save execution plan to file."""
        plan_data = {
            'test_files': plan.test_files,
            'execution_order': plan.execution_order,
            'parallel_groups': plan.parallel_groups,
            'environment': plan.environment,
            'config': plan.config,
            'dependencies': plan.dependencies,
            'created_at': str(Path(__file__).stat().st_mtime)
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(plan_data, f, default_flow_style=False)
