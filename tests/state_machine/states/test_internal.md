# Run all tests
```bash
poetry run pytest
```


# Run specific test files
```bash
poetry run pytest tests/test_internal/test_base.py -v
poetry run pytest tests/test_internal/test_succeed.py -v
poetry run pytest tests/test_internal/test_json_path.py -v
```

# Run with coverage
```bash
poetry run pytest --cov=src.pkg.__internal__.states tests/test_internal/
```


# Run specific test class
```bash
poetry run pytest tests/test_internal/test_base.py::TestRetryRule -v
poetry run pytest tests/test_internal/test_json_path.py::TestJSONPathProcessor -v
```

# Run with parallel execution (if pytest-xdist installed)
```bash
poetry run pytest -n auto tests/
```
