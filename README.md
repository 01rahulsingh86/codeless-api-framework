# Codeless API Automation Framework

A powerful framework for writing API tests in natural language with automatic response chaining, beautiful HTML reports, and seamless CI/CD integration.

## 🚀 Features

- **Natural Language Testing**: Write API tests in simple, readable English
- **Response Chaining**: Use data from one API call in subsequent calls automatically
- **Beautiful HTML Reports**: Generate professional-looking test reports with interactive features
- **CI/CD Integration**: Built-in planner-executor-reporter agent pattern for pipeline integration
- **Parallel Execution**: Run tests in parallel for faster execution
- **Environment Management**: Support for multiple test environments
- **Extensive Validations**: Rich validation options for API responses
- **Variable Extraction**: Extract and reuse variables across test steps

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Writing Tests](#writing-tests)
- [Configuration](#configuration)
- [CI/CD Integration](#cicd-integration)
- [Examples](#examples)
- [API Reference](#api-reference)

## 🛠 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from Source

```bash
git clone https://github.com/your-org/codeless-api-framework.git
cd codeless-api-framework
pip install -r requirements.txt
pip install -e .
```

### Using Docker

```bash
docker build -t codeless-api-framework .
docker run -v $(pwd)/tests:/app/tests codeless-api-framework
```

## 🏃‍♂️ Quick Start

### 1. Initialize a New Project

```bash
python main.py init
```

This creates the basic project structure:
```
your-project/
├── tests/
├── config/
├── reports/
├── examples/
└── config/framework.yml
```

### 2. Write Your First Test

Create a test file `tests/sample_test.txt`:

```text
Test: API Health Check
Description: Verify the API is responding correctly

- Check Health: GET https://api.example.com/health
  Status code should be 200
  Response should contain "status"

- Get API Version: GET https://api.example.com/version
  Status code should be 200
  Extract api_version from response.version
```

### 3. Run the Tests

```bash
python main.py run
```

### 4. View the Report

Open the generated HTML report in your browser:
```bash
open reports/latest_report.html
```

## ✍ Writing Tests

### Natural Language Format

Tests can be written in simple, natural language:

```text
Test: User Authentication
Description: Test user login and token management

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
```

### YAML Format

For more complex tests, use YAML format:

```yaml
name: User Management Tests
tests:
  - name: Create User
    steps:
      - name: Create User
        method: POST
        url: "{{base_url}}/users"
        body:
          username: "testuser"
          email: "test@example.com"
        expected_status: 201
        extract_variables:
          user_id: "id"
```

### Response Chaining

Use variables from previous responses:

```text
- Create User: POST {{base_url}}/users
  Body:
    username: testuser
  Extract user_id from response.id

- Get User: GET {{base_url}}/users/{{user_id}}
  Status code should be 200
```

### Validations

Built-in validation options:

```text
- Status code validations
  Status code should be 200
  Status code should be 201

- Content validations
  Response should contain "success"
  Response should not contain "error"

- Field validations
  username should be "testuser"
  status should not be "error"
```

## ⚙️ Configuration

### Framework Configuration

Create `config/framework.yml`:

```yaml
test_directory: tests
parallel_execution: true
max_parallel_tests: 5
timeout: 300
fail_fast: false

global_variables:
  base_url: "https://api.example.com"
  api_version: "v1"

environments:
  staging:
    variables:
      base_url: "https://staging-api.example.com"
  
  production:
    variables:
      base_url: "https://api.example.com"

reporting:
  html: true
  json: true
  junit: false
  output_directory: reports

notifications:
  slack:
    webhook_url: "YOUR_SLACK_WEBHOOK_URL"
```

### Environment Variables

Set environment variables with `API_TEST_` prefix:

```bash
export API_TEST_BASE_URL=https://api.example.com
export API_TEST_API_KEY=your-api-key
export API_TEST_TIMEOUT=30
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
name: API Tests
on: [push, pull_request]

jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -e .
    
    - name: Run API Tests
      env:
        API_TEST_BASE_URL: ${{ secrets.API_BASE_URL }}
        API_TEST_API_KEY: ${{ secrets.API_KEY }}
      run: |
        python main.py run --environment production --parallel
    
    - name: Upload Reports
      uses: actions/upload-artifact@v3
      with:
        name: api-test-reports
        path: reports/
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('API Tests') {
            steps {
                sh '''
                    python main.py run \
                        --environment production \
                        --parallel \
                        --output reports/${BUILD_NUMBER}
                '''
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: '*.html',
                        reportName: 'API Test Report'
                    ])
                }
            }
        }
    }
}
```

## 📚 Examples

### Basic API Testing

```text
Test: Basic CRUD Operations
Description: Test create, read, update, delete operations

- Create Item: POST {{base_url}}/items
  Body:
    name: "Test Item"
    price: 99.99
  Status code should be 201
  Extract item_id from response.id

- Read Item: GET {{base_url}}/items/{{item_id}}
  Status code should be 200
  name should be "Test Item"

- Update Item: PUT {{base_url}}/items/{{item_id}}
  Body:
    name: "Updated Item"
  Status code should be 200
  name should be "Updated Item"

- Delete Item: DELETE {{base_url}}/items/{{item_id}}
  Status code should be 204
```

### Complex Workflow Testing

```text
Test: E-commerce Order Flow
Description: Complete order processing workflow

Setup:
- Login Admin: POST {{base_url}}/auth/login
  Body:
    username: admin
    password: adminpass
  Extract admin_token from response.token

Test Steps:
- Create Product: POST {{base_url}}/products
  Headers:
    Authorization: Bearer {{admin_token}}
  Body:
    name: "Test Product"
    price: 29.99
    stock: 100
  Extract product_id from response.id

- Create Customer: POST {{base_url}}/customers
  Body:
    name: "John Doe"
    email: "john@example.com"
  Extract customer_id from response.id

- Create Order: POST {{base_url}}/orders
  Body:
    customer_id: {{customer_id}}
    items:
      - product_id: {{product_id}}
        quantity: 2
  Extract order_id from response.id

- Process Payment: POST {{base_url}}/orders/{{order_id}}/pay
  Body:
    amount: 59.98
    method: "credit_card"
  Status code should be 200
```

## 📖 API Reference

### Command Line Interface

```bash
# Run all tests
python main.py run

# Run specific tests
python main.py run --tests test1.txt test2.yml

# Use specific environment
python main.py run --environment staging

# Enable parallel execution
python main.py run --parallel

# Fail fast on first error
python main.py run --fail-fast

# Validate test files
python main.py validate tests/*.txt

# Create execution plan
python main.py plan --output plan.yml

# Initialize new project
python main.py init
```

### Test File Syntax

#### Step Structure

Each test step follows this pattern:

```
Step Name: HTTP_METHOD URL
  Headers:
    Header-Name: Value
  Body:
    field: value
  Status code should be STATUS_CODE
  Extract variable_name from response.path
  Validation rules
```

#### Supported HTTP Methods

- GET
- POST
- PUT
- DELETE
- PATCH
- HEAD
- OPTIONS

#### Variable Substitution

Use `{{variable_name}}` syntax for substitution:

```text
URL: {{base_url}}/users/{{user_id}}
Body:
  token: {{auth_token}}
```

#### Response Extraction

Extract data from API responses:

```text
Extract user_id from response.id
Extract token from response.access_token
Extract items from response.data.items
```

#### Validation Rules

```text
# Status code validation
Status code should be 200

# Content validation
Response should contain "success"
Response should not contain "error"

# Field validation
username should be "testuser"
status should not be "error"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Documentation](https://your-org.github.io/codeless-api-framework)
- 🐛 [Issue Tracker](https://github.com/your-org/codeless-api-framework/issues)
- 💬 [Discussions](https://github.com/your-org/codeless-api-framework/discussions)

## 🎯 Roadmap

- [ ] Web UI for test management
- [ ] Performance testing integration
- [ ] Mock server support
- [ ] Test data management
- [ ] Advanced reporting features
- [ ] Integration with popular test management tools
