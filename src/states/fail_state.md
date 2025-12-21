## fail_state.py

1. Required Error field for error codes
2. Optional Cause field for error descriptions
3. Terminal state validation (no Next, End, or paths)
4. Returns StateError on execution
5. Ignores input data

### Comprehensive test suite with 28 tests:

* ✅ Initialization and validation
* ✅ Execution always returns errors
* ✅ Error details verification
* ✅ AWS standard error codes
* ✅ Input ignored correctly
* ✅ JSON serialization
* ✅ Multiple and concurrent executions
* ✅ Error consistency checks
