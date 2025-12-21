# State Machine AMZ Python 🔄

[![CI](https://github.com/hussainpithawala/state-machine-amz-py/workflows/CI/badge.svg)](https://github.com/hussainpithawala/state-machine-amz-py/actions)
[![PyPI version](https://badge.fury.io/py/state-machine-amz-py.svg)](https://badge.fury.io/py/state-machine-amz-py)
[![Python Support](https://img.shields.io/pypi/pyversions/state-machine-amz-py)](https://pypi.org/project/state-machine-amz-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/hussainpithawala/state-machine-amz-py/branch/main/graph/badge.svg)](https://codecov.io/gh/hussainpithawala/state-machine-amz-py)

A production-ready Python implementation of AWS Step Functions (Amazon States Language) with persistent execution tracking using PostgreSQL.

## 🌟 Features

### Core State Machine
- ✅ **Full ASL Support** - Complete implementation of Amazon States Language
- ✅ **All State Types** - Task, Pass, Choice, Wait, Succeed, Fail, Parallel, Map
- ✅ **Error Handling** - Catch, Retry with exponential backoff
- ✅ **JSONPath Support** - Advanced input/output processing
- ✅ **Async Execution** - Native async/await support
- ✅ **Type Safe** - Full type hints throughout

### Persistence Layer
- ✅ **Automatic Persistence** - Execution state saved at every step
- ✅ **PostgreSQL Backend** - Reliable, production-ready storage
- ✅ **State History** - Complete audit trail of all state transitions
- ✅ **Query Support** - List, filter, and count executions
- ✅ **Statistics** - Execution metrics and analytics
- ✅ **Connection Pooling** - Efficient database connection management

### Production Ready
- ✅ **Well Tested** - 95%+ test coverage
- ✅ **Fully Documented** - Comprehensive documentation and examples
- ✅ **Type Checked** - MyPy compatible
- ✅ **CI/CD** - Automated testing and releases
- ✅ **Performance** - Optimized for high-throughput workloads

## 📦 Installation

### Using Poetry (Recommended)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Clone and install
git clone https://github.com/hussainpithawala/state-machine-amz-py.git
cd state-machine-amz-py
poetry install

# With all optional dependencies
poetry install --with dev,async,docs
```

### Using pip

```bash
pip install state-machine-amz-py
```

### From Source

```bash
git clone https://github.com/hussainpithawala/state-machine-amz-py.git
cd state-machine-amz-py

# Using Poetry
poetry install

# Or using pip
pip install -e .
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/hussainpithawala/state-machine-amz-py.git
cd state-machine-amz-py

# Install with Poetry (includes dev dependencies)
poetry install --with dev

# Or with pip
pip install -e ".[dev]"
```

## 🚀 Quick Start

### Basic State Machine

```python
import asyncio
from src.machine import StateMachine

# Define state machine
definition = {
    "StartAt": "HelloWorld",
    "States": {
        "HelloWorld": {
            "Type": "Pass",
            "Result": "Hello, World!",
            "End": True
        }
    }
}

# Create and execute
async def main():
    sm = StateMachine.from_dict(definition)
    execution = await sm.execute({"name": "Alice"})
    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")

asyncio.run(main())
```

### With Persistence

```python
import asyncio
from src.machine import PersistentStateMachine
from src.repository import PersistenceManager, RepositoryConfig

# Setup persistence
config = RepositoryConfig(
    strategy="postgres",
    connection_url="postgresql://user:pass@localhost/db"
)
manager = PersistenceManager(config)
manager.initialize()

# Define workflow
definition = """
{
    "StartAt": "ProcessOrder",
    "States": {
        "ProcessOrder": {
            "Type": "Task",
            "Resource": "process-order",
            "Next": "SendNotification"
        },
        "SendNotification": {
            "Type": "Task",
            "Resource": "send-email",
            "End": true
        }
    }
}
"""

async def main():
    # Create persistent state machine
    sm = PersistentStateMachine.create_from_json(
        definition,
        persistence_manager=manager,
        state_machine_id="order-workflow-v1"
    )

    # Execute with automatic persistence
    execution = await sm.execute(
        input_data={"order_id": "12345"},
        execution_name="Order-12345"
    )

    # Query results
    history = await sm.get_execution_history(execution.id)
    print(f"States executed: {len(history)}")

    # List all executions
    executions = sm.list_executions()
    print(f"Total executions: {len(executions)}")

asyncio.run(main())
```

### With Task Handlers

```python
from src.states import with_execution_context

# Create execution context
class TaskContext:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, name, handler):
        self.handlers[name] = handler

    def get_task_handler(self, resource):
        return self.handlers.get(resource)

# Register handlers
task_ctx = TaskContext()

async def process_order(resource, input_data, parameters=None):
    """Process order handler."""
    order_id = input_data["order_id"]
    # Process order logic here
    return {
        "order_id": order_id,
        "status": "processed",
        "timestamp": datetime.utcnow().isoformat()
    }

task_ctx.register_handler("process-order", process_order)

# Create context and execute
exec_context = with_execution_context({}, task_ctx)
execution = await sm.execute(
    input_data={"order_id": "12345"},
    task_exec_context=exec_context
)
```

## 📖 State Types

### Task State

Execute custom functions or AWS Lambda:

```json
{
    "Type": "Task",
    "Resource": "my-function",
    "Parameters": {
        "value.$": "$.input",
        "static": "parameter"
    },
    "ResultPath": "$.result",
    "Retry": [{
        "ErrorEquals": ["States.TaskFailed"],
        "MaxAttempts": 3,
        "BackoffRate": 2.0
    }],
    "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "ErrorHandler"
    }],
    "Next": "NextState"
}
```

### Choice State

Conditional branching:

```json
{
    "Type": "Choice",
    "Choices": [{
        "Variable": "$.value",
        "NumericGreaterThan": 100,
        "Next": "HighValue"
    }, {
        "Variable": "$.value",
        "NumericLessThanEquals": 100,
        "Next": "LowValue"
    }],
    "Default": "DefaultState"
}
```

### Parallel State

Execute branches in parallel:

```json
{
    "Type": "Parallel",
    "Branches": [
        {
            "StartAt": "Branch1",
            "States": {
                "Branch1": {
                    "Type": "Task",
                    "Resource": "task1",
                    "End": true
                }
            }
        },
        {
            "StartAt": "Branch2",
            "States": {
                "Branch2": {
                    "Type": "Task",
                    "Resource": "task2",
                    "End": true
                }
            }
        }
    ],
    "Next": "Aggregate"
}
```

### Map State

Iterate over arrays:

```json
{
    "Type": "Map",
    "ItemsPath": "$.items",
    "MaxConcurrency": 5,
    "Iterator": {
        "StartAt": "ProcessItem",
        "States": {
            "ProcessItem": {
                "Type": "Task",
                "Resource": "process",
                "End": true
            }
        }
    },
    "End": true
}
```

## 🗄️ Database Setup

### PostgreSQL

```bash
# Create database
createdb statemachine

# Or using Docker
docker run -d \
  --name postgres-statemachine \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=statemachine \
  -p 5432:5432 \
  postgres:15
```

### Schema

The schema is automatically created on initialization:

- `executions` - Execution records
- `state_history` - State transition history
- `execution_statistics` - Aggregated metrics

## 🔧 Configuration

### Repository Config

```python
config = RepositoryConfig(
    strategy="postgres",
    connection_url="postgresql://user:pass@host:port/db",
    options={
        "max_open_conns": 25,      # Max connections
        "max_overflow": 10,        # Additional connections
        "pool_timeout": 30,        # Timeout in seconds
        "conn_max_lifetime": 300,  # Connection lifetime
        "echo": False              # SQL logging
    }
)
```

### Environment Variables

```bash
# Database connection
export DATABASE_URL="postgresql://user:pass@localhost/db"
export POSTGRES_TEST_URL="postgresql://user:pass@localhost/testdb"

# Application settings
export STATE_MACHINE_TIMEOUT=300
export LOG_LEVEL=INFO
```

## 📊 Querying Executions

### List Executions

```python
from src.repository import ExecutionFilter

# Filter executions
filter = ExecutionFilter(
    status="SUCCEEDED",
    state_machine_id="workflow-v1",
    start_after=datetime(2025, 1, 1),
    limit=10,
    offset=0
)

executions = sm.list_executions(filter)
for exec in executions:
    print(f"{exec.name}: {exec.status}")
```

### Get Execution History

```python
history = await sm.get_execution_history("exec-123")
for state in history:
    duration = (state.end_time - state.start_time).total_seconds()
    print(f"{state.state_name}: {state.status} ({duration:.2f}s)")
```

### Statistics

```python
stats = manager.repository.get_statistics("workflow-v1")
for status, stat in stats.by_status.items():
    print(f"{status}:")
    print(f"  Count: {stat.count}")
    print(f"  Avg Duration: {stat.avg_duration_seconds:.2f}s")
    print(f"  P95 Duration: {stat.p95_duration:.2f}s")
```

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/ -m "not integration"

# Integration tests
pytest tests/ -m integration

# With coverage
pytest --cov=src --cov-report=html
```

### Run Examples

```bash
# Simple workflow
python examples/demo_execution_flow.py

# Persistent workflow
python examples/demo_execution_flow_persistent.py
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         State Machine Engine            │
│  ┌───────────────────────────────────┐  │
│  │  State Types                      │  │
│  │  - Task, Pass, Choice, Wait       │  │
│  │  - Parallel, Map, Succeed, Fail   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Execution Engine                 │  │
│  │  - Input/Output Processing        │  │
│  │  - Error Handling & Retry         │  │
│  │  - State Transitions              │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│       Persistence Layer                 │
│  ┌───────────────────────────────────┐  │
│  │  Repository Interface             │  │
│  │  - Abstract persistence API       │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  PostgreSQL Implementation        │  │
│  │  - SQLAlchemy ORM                 │  │
│  │  - Connection Pooling             │  │
│  │  - JSONB Support                  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           PostgreSQL                    │
│  - executions                           │
│  - state_history                        │
│  - execution_statistics                 │
└─────────────────────────────────────────┘
```

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION_GUIDE.md)
- [State Machine Guide](docs/PERSISTENT_STATE_MACHINE_README.md)
- [API Reference](docs/API.md)
- [Examples](examples/)
- [Contributing Guide](CONTRIBUTING.md)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/hussainpithawala/state-machine-amz-py.git
cd state-machine-amz-py

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type check
mypy src/
```

### Running CI Locally

```bash
# Install act (GitHub Actions runner)
brew install act  # macOS
# or download from: https://github.com/nektos/act

# Run CI workflow
act push
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [AWS Step Functions](https://aws.amazon.com/step-functions/)
- Based on [Amazon States Language](https://states-language.net/)
- PostgreSQL persistence using [SQLAlchemy](https://www.sqlalchemy.org/)


## 👨‍💻 Author

**Hussain Pithawala**
- LinkedIn: [hussainpithawala](https://www.linkedin.com/in/hussainpithawala)
- GitHub: [@hussainpithawala](https://github.com/hussainpithawala)

## 📮 Contact

- **Issues**: [GitHub Issues](https://github.com/hussainpithawala/state-machine-amz-py/issues)
- **Discussions**: [GitHub Discussions](https://github.com/hussainpithawala/state-machine-amz-py/discussions)
- **Email**: hussainpithawala@hotmail.com

## 🔗 Related Projects

- [state-machine-amz-go](https://github.com/hussainpithawala/state-machine-amz-go) - Go implementation
- [state-machine-amz-ruby](https://github.com/hussainpithawala/state-machine-amz-ruby) - Ruby implementation

## 📈 Roadmap

- [ ] DynamoDB persistence backend
- [ ] Redis persistence backend
- [ ] In-memory persistence for testing
- [ ] Distributed execution support
- [ ] REST API server
- [ ] Web-based execution viewer
- [ ] CloudFormation/Terraform support
- [ ] Prometheus metrics exporter

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=hussainpithawala/state-machine-amz-py&type=Date)](https://star-history.com/#hussainpithawala/state-machine-amz-py&Date)

---

**Made with ❤️ by the State Machine Community**
