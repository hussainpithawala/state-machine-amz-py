# Choice State
## Key Features:

### ChoiceRule dataclass with all comparison operators:

* ✅ String comparisons (equals, less than, greater than, etc.)
* ✅ Numeric comparisons with automatic type conversion
* ✅ Boolean comparisons with string-to-bool conversion
* ✅ Timestamp comparisons with multiple format support


### ChoiceState class extending BaseState:

* ✅ Validates that Choice states cannot have Next or End fields
* ✅ Evaluates choices in order, returns first match
* ✅ Supports default state when no choices match
* ✅ Applies InputPath, ResultPath, and OutputPath correctly


### Compound operators:

* ✅ AND: All conditions must be true
* ✅ OR: At least one condition must be true
* ✅ NOT: Negates the result

### Robust validation:

* ✅ Ensures Variable is present for comparison operators
* ✅ Ensures at least one operator is specified
* ✅ Ensures Next is specified for top-level choices
* ✅ Eecursively validates nested compound operators


## test_choice_state.py - Comprehensive Test Coverage:

93 test cases covering:

* ✅ All comparison operators with various data types
* ✅ Type conversions (string-to-number, string-to-bool, Unix timestamps)
* ✅ Logical operators (AND, OR, NOT) with nesting
* ✅ Multiple choices with first-match semantics
* ✅ Path processing (InputPath, ResultPath, OutputPath)
* ✅ Error cases (no match without default, missing variables)
* ✅ Edge cases (deeply nested variables, empty objects)
* ✅ Serialization (to_dict, to_json)
