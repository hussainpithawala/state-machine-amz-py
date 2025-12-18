## Task State

### Core Implementation
TaskState class with full AWS States Language support
TaskHandler and ExecutionContext protocols
DefaultTaskHandler for delegation
Complete retry logic with exponential backoff
Error catching with catch policies
Path processing (InputPath, ResultPath, OutputPath, ResultSelector)
Async/await pattern for Python


### Test-Case(s)
#### Direct support for TaskHandler (without registry in execution-context)

1. Basic execution
2. Path processing (InputPath, ResultPath, OutputPath)
3. ResultSelector
4. Timeout handling
5. Retry with success
6. Retry exhaustion
7. Catch policies
8. Validation rules
9. Error matching

### Test-Case(s)
#### In-Direct support for TaskHandler (preparing a central registry )

1. Handler registration and execution
2. Parameter expansion
3. Timeout with ExecutionContext
4. Fallback behavior
5. Error handling
6. Retry logic with backoff timing
7. Catch logic with error info
8. Real-world usage examples
