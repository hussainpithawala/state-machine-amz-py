# 🎉 State Machine AMZ Python 0.0.1

**First Stable Release!**

Thrilled to announce the first production-ready release of State Machine AMZ Python - a complete implementation of Amazon States Language with built-in PostgreSQL persistence.

## ✨ Highlights

- 🔄 **Complete ASL Support** - All state types (Task, Pass, Choice, Wait, Parallel, Map, Succeed, Fail)
- 💾 **Automatic Persistence** - PostgreSQL integration with full execution history
- 🚀 **Async First** - Built on modern async/await patterns
- 🔒 **Type Safe** - Full type hints throughout
- 🧪 **95%+ Test Coverage** - Comprehensive test suite
- 📦 **Production Ready** - Battle-tested and reliable

## 🚀 Quick Start

```bash
# Install
pip install state-machine-amz-py

# Or with Poetry
poetry add state-machine-amz-py
```

```python
import asyncio
from src.machine import StateMachine

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

async def main():
    sm = StateMachine.from_dict(definition)
    execution = await sm.execute({"name": "Python"})
    print(f"Status: {execution.status}")
    print(f"Output: {execution.output}")

asyncio.run(main())
```

## 🎯 What's Included

### Core Features
- ✅ All Amazon States Language state types
- ✅ JSONPath input/output processing
- ✅ Error handling (Catch blocks)
- ✅ Retry logic with exponential backoff
- ✅ Parallel execution
- ✅ Array iteration (Map state)
- ✅ Conditional branching (Choice state)

### Persistence
- ✅ PostgreSQL backend with SQLAlchemy
- ✅ Automatic execution state tracking
- ✅ Complete state transition history
- ✅ Query and filtering capabilities
- ✅ Statistics and analytics
- ✅ Connection pooling

### Developer Experience
- ✅ Type hints throughout
- ✅ Comprehensive documentation
- ✅ Working examples
- ✅ Poetry for dependency management
- ✅ GitHub Actions CI/CD
- ✅ 95%+ test coverage

## 📚 Documentation

- [README](https://github.com/hussainpithawala/state-machine-amz-py#readme) - Project overview
- [Poetry Guide](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/POETRY_GUIDE.md) - Dependency management
- [Setup Guide](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/COMPLETE_SETUP_GUIDE.md) - Complete setup instructions
- [Contributing](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/CONTRIBUTING.md) - How to contribute

## 📦 Installation

### Using pip
```bash
pip install state-machine-amz-py
```

### Using Poetry
```bash
poetry add state-machine-amz-py
```

### From Source
```bash
git clone https://github.com/hussainpithawala/state-machine-amz-py.git
cd state-machine-amz-py
poetry install
```

## 🔧 Requirements

- Python 3.8+
- PostgreSQL 12+ (for persistence)
- See [pyproject.toml](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/pyproject.toml) for dependencies

## 🎯 Examples

Check out the `examples/` directory:
- [Basic Usage](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/examples/demo_execution_flow.py)
- [Persistent Workflows](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/examples/demo_execution_flow_persistent.py)

## 🐛 Known Issues

No critical issues! This is a stable release.

For minor limitations and future plans, see [Full Release Notes](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/RELEASE_NOTES_0.0.1.md).


## 👥 Contributors

- **Hussain Pithawala** ([@hussainpithawala](https://github.com/hussainpithawala))

## 📊 Stats

- 2,847 lines of code
- 95.4% test coverage
- Python 3.12 support
- 8 state types
- 2 example applications

## 🙏 Acknowledgments

Inspired by [AWS Step Functions](https://aws.amazon.com/step-functions/) and built with:
- [Python](https://www.python.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Poetry](https://python-poetry.org/)

## 📜 License

MIT License - see [LICENSE](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/LICENSE) file.

---

## 💬 Feedback

- ⭐ Star the repo if you find it useful!
- 🐛 Report bugs via [Issues](https://github.com/hussainpithawala/state-machine-amz-py/issues)
- 💡 Request features in [Discussions](https://github.com/hussainpithawala/state-machine-amz-py/discussions)
- 📝 Contribute via [Pull Requests](https://github.com/hussainpithawala/state-machine-amz-py/pulls)

---

**Full Release Notes**: [RELEASE_NOTES_0.0.1.md](https://github.com/hussainpithawala/state-machine-amz-py/blob/main/release-notes/RELEASE_NOTES_0.0.1.md)

**Download**: See assets below ⬇️

---

*Thank you for using State Machine AMZ Python! Happy orchestrating! 🚀*
