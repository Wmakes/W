# W Language Specification 

W is a simple scripting language for basic computations, I/O, and control flow. It's interpreted via Python, with a focus on ease of use. Scripts use `.w` extension. 

## Design Principles
- **Simplicity**: Minimal syntax, no types beyond int/bool/string/array.
- **Error Handling**: Runtime errors are printed with line numbers; execution continues if possible.
- **Stateful**: Variables/arrays/functions persist in REPL or across file lines.
- **No Scoping**: Global scope only (no local variables in functions/loops).
- **Limits**: While loops capped at 1000 iterations to avoid hangs.

## Syntax Rules
- Case-sensitive.
- Statements end with newline or `;` (multi-statements per line).
- Comments: `# anything` (ignored).
- Strings: `"..."` or `'...'`.
- Numbers: Integers/floats, negatives supported (e.g., `-5.2`).
- Variables: Alphanumeric + `_`, start with letter/_. No quotes needed (but supported for compat).
- Indentation: Required for blocks (while/func), ended by `done`.
- Expressions: Math/logic with precedence (*/ before +-).

## Data Types
- **Int/Number**: Integers (e.g., 42, -5). Floats if decimal.
- **String**: Quoted text.
- **Bool**: `true`/`false`.
- **Array**: List of numbers or strings.
- No explicit type declarations (inferred).

## Statements and Commands

### Display: `show`
Displays value.  
Syntax: `show expr`  
Examples:  
`show "Hello"` → Hello  
`show myVar` → Value of myVar  

### Assignment: `int` / Expressions
Assigns to variable.  
Syntax: `int var expr` (or direct: `expr = var`)  
Examples:  
`int myNum 42`  
`int negative -5`  
`3 + 2 = sum` → sum = 5  

### Boolean: `bool`
Assigns boolean. Defaults to false.  
Syntax: `bool var [true|false]`  
Examples:  
`bool isOK true`  
`bool notOK` → false  

### Arrays (Numeric): `array`
Creates numeric array from comma-separated string.  
Syntax: `array "vals" arrayName`  
Examples:  
`array "1,2,-3" myArray` → [1, 2, -3]  

### Arrays (String): `array_str`
Creates string array.  
Syntax: `array_str "str1","str2",... arrayName`  
Examples:  
`array_str "ala","ma" words` → ['ala', 'ma']  

### Array Operations
- `leng arrayName` → Prints length.  
- `push arrayName value` → Appends value.  
- `pop arrayName` → Removes/prints last.  
- `get arrayName index [= var]` → Gets value (to var or print).  

### Math Expressions
Operators: `+ - * /` (precedence: */ first).  
Examples:  
`2 * 3 + 1 = 7`  

### Conditionals: `if`
Syntax: `if cond stmt [else stmt]`  
Cond: `expr op expr` (op: = != > < >= <=) or logical (`and`/`or`/`not`).  
Examples:  
`if x > 5 show "large" else show "small"`  
`if not isOK show "failed"`  

### Loops: `while`
Indent block, end with `done`.  
Syntax:  
`while cond`  
  `stmt`  
`done`  
Examples: See guide. Limit: 1000 iterations.  

### Functions: `func`
Global, no params/returns. Indent block.  
Syntax:  
`func name`  
`stmt`  
`done`  
`call name`  

### Input: `input`
Syntax: `input "prompt" = var`  
Reads from stdin.  

### Time/Date: `time` / `date` / `datetime`
Prints current time/date.  

### Sleep: `sleep`
Syntax: `sleep seconds`  
Pauses execution.  

### Random: `random`
Syntax: `random start end = var`  
Integer in [start, end] (negatives OK).  

### Files: `write` / `read`
Syntax:  
`write "text" "file.txt"` (to temp dir)  
`read "file.txt" = var`  
### Clear's 
`clear` clears the var's 
`clear-output` clears the output in the terminal 
### End: `END`
Stops program execution.  


## Semantics and Rules
- **Evaluation**: Left-to-right, with op precedence.
- **Type Coercion**: Numbers in math; strings concat with + if mixed.
- **Errors**: Printed, non-fatal (continues).
- **Files**: Written/read from system temp dir.
- **REPL**: Stateful (vars persist).
- **Line Limits**: Max 1000 lines per script.



This spec is exhaustive based on v0.9 interpreter. For extensions, contribute on GitHub.
