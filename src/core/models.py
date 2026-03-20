from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class APIRequest:
    method: HttpMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    auth: Optional[Dict[str, str]] = None
    timeout: int = 30
    name: Optional[str] = None


@dataclass
class APIResponse:
    status_code: int
    headers: Dict[str, str]
    body: Any
    response_time: float
    request: APIRequest
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TestStep:
    name: str
    request: APIRequest
    expected_status: int = 200
    validations: List[str] = field(default_factory=list)
    extract_variables: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class TestCase:
    name: str
    description: str
    steps: List[TestStep]
    setup: List[TestStep] = field(default_factory=list)
    teardown: List[TestStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timeout: int = 300


@dataclass
class TestResult:
    test_name: str
    status: TestStatus
    steps: List[Dict[str, Any]]
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    name: str
    tests: List[TestCase]
    global_setup: List[TestStep] = field(default_factory=list)
    global_teardown: List[TestStep] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestReport:
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    total_time: float
    test_results: List[TestResult]
    generated_at: datetime = field(default_factory=datetime.now)
    environment: Dict[str, Any] = field(default_factory=dict)
