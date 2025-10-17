import os
import random
import tempfile
import time
import re
from datetime import datetime
from tkinter import filedialog, Tk

TMP_DIR = tempfile.gettempdir()
DEBUG = False  # Turn on for detailed internal debugging prints
MAX_ITERATIONS = 1000  # Safety cap for while loops to avoid infinite loops

# ---------------------------
# LEXER / TOKENIZER
# ---------------------------
# Regular expressions are checked in order via a combined regex.
TOKEN_SPEC = [
    ("TRUE", r"\btrue\b"),
    ("FALSE", r"\bfalse\b"),
    ("NOT", r"\bnot\b"),
    ("AND", r"\band\b"),
    ("OR", r"\bor\b"),
    ("OP", r"[\+\-\*/=<>!]+"),
    ("NUMBER", r"-?\d+(\.\d+)?|-?\d+"),
    ("STRING", r'"[^"]*"|\'[^\']*\''),
    ("ID", r"[A-Za-z_]\w*"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t]+"),
    ("SEMICOLON", r";"),
    ("COMMA", r","),
    ("COMMENT", r"#.*"),
]
TOKEN_REGEX = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
get_token = re.compile(TOKEN_REGEX).match


class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value


def tokenize(code):
    """
    Convert source string into a linear list of Token objects.
    Skips whitespace, newlines and comments.
    Raises SyntaxError on unknown tokens.
    """
    pos = 0
    tokens = []
    while pos < len(code):
        m = get_token(code, pos)
        if not m:
            raise SyntaxError(f"Unknown token at position {pos}: {code[pos:pos + 10]!r}")
        typ = m.lastgroup
        val = m.group(typ)
        if typ not in ("SKIP", "NEWLINE", "COMMENT"):
            tokens.append(Token(typ, val))
        pos = m.end()
    return tokens


# ---------------------------
# AST NODES
# ---------------------------
# Minimal AST node classes. They are simple containers used by the parser
# and evaluated by the runner. Add fields as needed for more complex features.

class Number:
    def __init__(self, value):
        # store as int if no dot, otherwise float
        self.value = float(value) if '.' in str(value) else int(value)


class StringNode:
    def __init__(self, value):
        # strip surrounding quotes
        self.value = value[1:-1] if value.startswith(('"', "'")) else value


class BoolNode:
    def __init__(self, value):
        self.value = value == "true"


class Var:
    def __init__(self, name):
        # allow quoted variable names (rare) but normalize
        if name.startswith("'") or name.startswith('"'):
            self.name = name[1:-1]
        else:
            self.name = name


class BinOp:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right


class NotOp:
    def __init__(self, expr):
        self.expr = expr


class Assign:
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr


class BoolAssign:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Show:
    def __init__(self, expr):
        self.expr = expr


class Array:
    def __init__(self, values, name):
        self.values = values
        self.name = name


class ArrayStr:
    def __init__(self, values, name):
        self.values = values
        self.name = name


class Get:
    def __init__(self, array_name, index, result_var=None):
        self.array_name = array_name
        self.index = index
        self.result_var = result_var


class Leng:
    def __init__(self, name):
        self.name = name


class Push:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Pop:
    def __init__(self, name):
        self.name = name


class IfElse:
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body


class Cond:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right


class WhileNode:
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body


class Redo:
    def __init__(self, count, action):
        self.count = count
        self.action = action


class Func:
    def __init__(self, name, body):
        self.name = name
        self.body = body


class Call:
    def __init__(self, name):
        self.name = name


class InputNode:
    def __init__(self, prompt, varname):
        self.prompt = prompt
        self.varname = varname


class TimeNode:
    pass


class DateNode:
    pass


class DateTimeNode:
    pass


class Sleep:
    def __init__(self, seconds):
        self.seconds = seconds


class RandomNode:
    def __init__(self, start, end, varname):
        self.start = start
        self.end = end
        self.varname = varname


class Write:
    def __init__(self, text, filename):
        self.text = text
        self.filename = filename


class Read:
    def __init__(self, filename, varname):
        self.filename = filename
        self.varname = varname


class End:
    pass


# ---------------------------
# PARSER
# ---------------------------
# Recursive-descent style parser that consumes the flat token list and returns
# AST node(s). The parser intentionally stays small and focused on clarity.
class Parser:
    def __init__(self, tokens, line_number=0):
        self.tokens = tokens
        self.pos = 0
        self.line_number = line_number

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, typ):
        token = self.current()
        if token and token.type == typ:
            self.pos += 1
            return token.value
        raise SyntaxError(
            f"Line {self.line_number}: expected {typ}, got {token.type if token else 'EOF'}")

    def parse_var(self):
        token = self.current()
        if DEBUG:
            print(
                f"[DEBUG] parse_var: current token = {token.type if token else 'None'}:{token.value if token else 'None'}")
        if token and token.type in ('STRING', 'ID'):
            name = self.eat(token.type)
            return Var(name)
        raise SyntaxError(f"Line {self.line_number}: expected variable name (STRING or ID)")

    def parse_expr(self):
        # handle binary + - * / with left-associativity
        left = self.parse_term()
        while self.current() and self.current().type == 'OP' and self.current().value in ['+', '-', '*', '/']:
            op = self.eat('OP')
            right = self.parse_term()
            left = BinOp(left, op, right)
        return left

    def parse_term(self):
        token = self.current()
        if token.type == 'OP' and token.value == '-':
            self.eat('OP')
            if self.current() and self.current().type == 'NUMBER':
                number_val = '-' + self.eat('NUMBER')
                return Number(number_val)
            else:
                expr = self.parse_term()
                return BinOp(Number(0), '-', expr)
        elif token.type == 'NUMBER':
            return Number(self.eat('NUMBER'))
        elif token.type == 'STRING':
            return StringNode(self.eat('STRING'))
        elif token.type == 'ID':
            return self.parse_var()
        elif token.type == 'NOT':
            self.eat('NOT')
            expr = self.parse_term()
            return NotOp(expr)
        elif token.type == 'TRUE':
            self.eat('TRUE')
            return BoolNode(True)
        elif token.type == 'FALSE':
            self.eat('FALSE')
            return BoolNode(False)
        raise SyntaxError(f"Line {self.line_number}: unexpected token in expression: {token.type}")

    def parse_assign(self):
        # assignment where left side is variable name
        name = self.parse_var().name
        if self.current() and self.current().type == 'OP' and self.current().value == '-':
            self.eat('OP')
            if self.current() and self.current().type == 'NUMBER':
                number_val = '-' + self.eat('NUMBER')
                expr = Number(number_val)
            else:
                raise SyntaxError(f"Line {self.line_number}: expected number after '-'")
        elif self.current() and self.current().type in ('NUMBER', 'STRING'):
            expr = self.parse_term()
        else:
            expr = self.parse_expr()
        return Assign(name, expr)

    def parse_bool_assign(self):
        # boolean declaration/assignment: bool <name> [true|false]
        name = self.parse_var().name
        if DEBUG:
            print(
                f"[DEBUG] parse_bool_assign: name = {name}, current token = {self.current().type if self.current() else 'None'}:{self.current().value if self.current() else 'None'}")

        if self.current() and self.current().type in ('TRUE', 'FALSE'):
            value_token = self.current()
            value = self.eat(value_token.type)
            bool_value = value == 'true'
            if DEBUG:
                print(f"[DEBUG] parse_bool_assign: value = {value}, bool_value = {bool_value}")
            return BoolAssign(name, bool_value)
        else:
            # default to False if not specified
            if DEBUG:
                print(f"[DEBUG] parse_bool_assign: no value found, defaulting to False")
            return BoolAssign(name, False)

    def parse_show(self):
        expr = self.parse_expr()
        return Show(expr)

    def parse_array(self):
        # array expects a string literal like "1,2,3" followed by the name
        if self.current() and self.current().type == 'STRING':
            values_str = self.eat('STRING').strip('"')
            values = []
            for val in values_str.split(','):
                val = val.strip()
                # allow negative integers
                if val and (val.replace('-', '').isdigit() or (
                        val.count('-') == 1 and val[0] == '-' and val[1:].isdigit())):
                    values.append(Number(int(val)))
            name = self.parse_var().name
            return Array(values, name)
        raise SyntaxError(f"Line {self.line_number}: expected string with array values")

    def parse_array_str(self):
        # gather multiple string literals separated by commas, then the array name
        values = []
        while self.current() and self.current().type in ('STRING', 'COMMA'):
            if self.current().type == 'STRING':
                values.append(StringNode(self.eat('STRING')))
            elif self.current().type == 'COMMA':
                self.eat('COMMA')
            else:
                break
        name = self.parse_var().name
        return ArrayStr(values, name)

    def parse_get(self):
        # get <array> <index> [= var]
        array_name = self.parse_var().name
        index = self.parse_expr()
        result_var = None
        if self.current() and self.current().value == '=':
            self.eat('OP')
            result_var = self.parse_var().name
        return Get(array_name, index, result_var)

    def parse_leng(self):
        name = self.parse_var().name
        return Leng(name)

    def parse_push(self):
        name = self.parse_var().name
        value = self.parse_expr()
        return Push(name, value)

    def parse_pop(self):
        name = self.parse_var().name
        return Pop(name)

    def parse_cond(self):
        # condition parser supports boolean logic and comparison ops.
        left = self.parse_expr()

        # boolean chaining with AND / OR (right-associative here)
        if self.current() and self.current().type in ('AND', 'OR'):
            op_token = self.current()
            self.eat(op_token.type)
            right = self.parse_cond()
            return Cond(left, op_token.type.lower(), right)

        # comparison operators
        if self.current() and self.current().type == 'OP':
            op = self.eat('OP')
            right = self.parse_expr()
            return Cond(left, op, right)

        # fallback: regular expression (e.g. numbers or vars evaluated truthily)
        return left

    def parse_if(self):
        cond = self.parse_cond()
        then_body = self.parse_stmt()
        else_body = None
        if self.current() and self.current().value == 'else':
            self.eat('ID')
            else_body = self.parse_stmt()
        return IfElse(cond, then_body, else_body)

    def parse_while(self):
        cond = self.parse_cond()
        return WhileNode(cond, None)

    def parse_redo(self):
        count = self.parse_expr()
        action = self.parse_stmt()
        return Redo(count, action)

    def parse_func(self):
        name = self.parse_var().name
        return Func(name, None)

    def parse_call(self):
        name = self.parse_var().name
        return Call(name)

    def parse_input(self):
        prompt = self.parse_expr()
        if self.current() and self.current().value == '=':
            self.eat('OP')
            varname = self.parse_var().name
            return InputNode(prompt, varname)
        raise SyntaxError(f"Line {self.line_number}: expected '=' after input")

    def parse_time(self):
        return TimeNode()

    def parse_date(self):
        return DateNode()

    def parse_datetime(self):
        return DateTimeNode()

    def parse_sleep(self):
        seconds = self.parse_expr()
        return Sleep(seconds)

    def parse_random(self):
        start = self.parse_expr()
        end = self.parse_expr()
        if self.current() and self.current().value == '=':
            self.eat('OP')
            varname = self.parse_var().name
            return RandomNode(start, end, varname)
        raise SyntaxError(f"Line {self.line_number}: expected '=' after random")

    def parse_write(self):
        text = self.parse_expr()
        filename = self.parse_expr()
        return Write(text, filename)

    def parse_read(self):
        filename = self.parse_expr()
        if self.current() and self.current().value == '=':
            self.eat('OP')
            varname = self.parse_var().name
            return Read(filename, varname)
        raise SyntaxError(f"Line {self.line_number}: expected '=' after read")

    def parse_end(self):
        return End()

    def parse_stmt(self):
        # parse a single statement or expression from the current token stream
        token = self.current()
        if not token:
            return None
        if DEBUG:
            print(f"[DEBUG] Parsing statement: {token.value}")
            print(f"[DEBUG] All tokens: {[f'{t.type}:{t.value}' for t in self.tokens]}")
            print(f"[DEBUG] Current position: {self.pos}")

        if token.type == 'ID':
            cmd = self.eat('ID')
            if cmd == 'show':
                return self.parse_show()
            elif cmd == 'int':
                name = self.parse_var().name
                if self.current() and self.current().type == 'OP' and self.current().value == '-':
                    self.eat('OP')
                    if self.current() and self.current().type == 'NUMBER':
                        value = '-' + self.eat('NUMBER')
                        return Assign(name, Number(value))
                    else:
                        raise SyntaxError(f"Line {self.line_number}: expected number after '-'")
                elif self.current() and self.current().type == 'NUMBER':
                    value = self.eat('NUMBER')
                    return Assign(name, Number(value))
                else:
                    expr = self.parse_expr()
                    return Assign(name, expr)
            elif cmd == 'bool':
                return self.parse_bool_assign()
            elif cmd == 'array':
                return self.parse_array()
            elif cmd == 'array_str':
                return self.parse_array_str()
            elif cmd == 'get':
                return self.parse_get()
            elif cmd == 'leng':
                return self.parse_leng()
            elif cmd == 'push':
                return self.parse_push()
            elif cmd == 'pop':
                return self.parse_pop()
            elif cmd == 'if':
                return self.parse_if()
            elif cmd == 'while':
                return self.parse_while()
            elif cmd == 'redo':
                return self.parse_redo()
            elif cmd == 'func':
                return self.parse_func()
            elif cmd == 'call':
                return self.parse_call()
            elif cmd == 'input':
                return self.parse_input()
            elif cmd == 'time':
                return self.parse_time()
            elif cmd == 'date':
                return self.parse_date()
            elif cmd == 'datetime':
                return self.parse_datetime()
            elif cmd == 'sleep':
                return self.parse_sleep()
            elif cmd == 'random':
                return self.parse_random()
            elif cmd == 'write':
                return self.parse_write()
            elif cmd == 'read':
                return self.parse_read()
            elif cmd == 'END':
                return self.parse_end()
            else:
                # fall back: treat as expression and possibly an assignment
                self.pos -= 1
                expr = self.parse_expr()
                if self.current() and self.current().type == 'OP' and self.current().value == '=':
                    self.eat('OP')
                    right_var = self.parse_var()
                    if DEBUG:
                        print(f"[DEBUG] Parsed assign: {right_var.name} = {expr}")
                    return Assign(right_var.name, expr)
                return expr
        elif token.type in ('NUMBER', 'STRING', 'ID', 'NOT', 'OP'):
            expr = self.parse_expr()
            if self.current() and self.current().type == 'OP' and self.current().value == '=':
                self.eat('OP')
                right_var = self.parse_var()
                if DEBUG:
                    print(f"[DEBUG] Parsed assign: {right_var.name} = {expr}")
                return Assign(right_var.name, expr)
            return expr
        raise SyntaxError(f"Line {self.line_number}: unknown command or expression: {token.value}")

    def parse(self):
        return self.parse_stmt()


# ---------------------------
# EVALUATOR / RUNNER
# ---------------------------
# Global runtime state for this simple interpreter.
variables = {}
arrays = {}
functions = {}
arrays_str = {}
stop_program = False


def eval_expr(node):
    """
    Evaluate an expression AST node and return its Python value.
    Supports Number, StringNode, BoolNode, Var, BinOp, NotOp.
    """
    if isinstance(node, Number):
        return node.value
    elif isinstance(node, StringNode):
        return node.value
    elif isinstance(node, BoolNode):
        return node.value
    elif isinstance(node, Var):
        if node.name in variables:
            return variables[node.name]
        elif node.name in arrays:
            return arrays[node.name]
        elif node.name in arrays_str:
            return arrays_str[node.name]
        raise NameError(f"No variable/array named: {node.name}")
    elif isinstance(node, BinOp):
        left = eval_expr(node.left)
        right = eval_expr(node.right)
        op = node.op
        result = None
        if op == '+':
            result = left + right
        elif op == '-':
            result = left - right
        elif op == '*':
            result = left * right
        elif op == '/':
            result = left / right
        if isinstance(left, int) and isinstance(right, int):
            return int(result)
        return result
    elif isinstance(node, NotOp):
        expr = eval_expr(node.expr)
        if not isinstance(expr, bool):
            raise ValueError("Operator 'not' requires a boolean value")
        return not expr
    raise TypeError(f"Unknown expression node type: {type(node)}")


def eval_cond(cond):
    """
    Evaluate conditions for 'if' and 'while'.
    Handles NotOp, Cond (comparisons and logical and/or), or simple expressions.
    """
    if isinstance(cond, NotOp):
        return not eval_cond(cond.expr)

    if isinstance(cond, Cond):
        # for boolean ops, evaluate subconditions recursively
        left = eval_cond(cond.left) if cond.op in ['and', 'or'] else eval_expr(cond.left)
        right = eval_cond(cond.right) if cond.op in ['and', 'or'] and hasattr(cond, 'right') else eval_expr(
            cond.right) if hasattr(cond, 'right') else None
        op = cond.op

        if op == 'and':
            return bool(left) and bool(right)
        elif op == 'or':
            return bool(left) or bool(right)

        # comparison operators: allow numeric-string coercion where reasonable
        if right is not None and op in ['=', '!=', '>', '<', '>=', '<=']:
            if isinstance(left, (int, float)) and isinstance(right, str) and right.replace('-', '').replace('.',
                                                                                                            '').isdigit():
                right = float(right) if '.' in right else int(right)
            elif isinstance(left, str) and isinstance(right, (int, float)) and left.replace('-', '').replace('.',
                                                                                                             '').isdigit():
                left = float(left) if '.' in left else int(left)

            if op == '=':
                return left == right
            elif op == '!=':
                return left != right
            elif op == '>':
                return left > right
            elif op == '<':
                return left < right
            elif op == '>=':
                return left >= right
            elif op == '<=':
                return left <= right

    # fallback for simple expression truthiness
    return bool(eval_expr(cond))


def run_node(node, line_number=0):
    """
    Execute a single AST node. Many node types map to imperative actions
    (assignments, array ops, control flow, I/O, time, etc.)
    """
    global stop_program
    global variables, arrays, arrays_str, functions
    if stop_program:
        return
    try:
        # CONDITIONS
        if isinstance(node, Cond):
            result = eval_cond(node)
            if DEBUG:
                print(f"[DEBUG] Cond result = {result}")
            return result
        elif isinstance(node, NotOp):
            result = not eval_cond(node.expr)
            if DEBUG:
                print(f"[DEBUG] NotOp result = {result}")
            return result

        # ASSIGNMENTS
        elif isinstance(node, Assign):
            value = eval_expr(node.expr)
            if DEBUG:
                print(f"[DEBUG] Assign '{node.name}' = {value}, variables before = {variables}")
            variables[node.name] = value
            if DEBUG:
                print(f"[DEBUG] Variables after assign = {variables}")
        elif isinstance(node, BoolAssign):
            if DEBUG:
                print(f"[DEBUG] BoolAssign '{node.name}' = {node.value}")
            variables[node.name] = node.value

        # DISPLAY / PRINT
        elif isinstance(node, Show):
            value = eval_expr(node.expr)
            if DEBUG:
                print(f"[DEBUG] Show value = {value}")
            print(value)

        # ARRAYS
        elif isinstance(node, Array):
            values = [eval_expr(v) for v in node.values]
            if DEBUG:
                print(f"[DEBUG] Array '{node.name}' = {values}")
            arrays[node.name] = values
        elif isinstance(node, ArrayStr):
            values = [eval_expr(v) for v in node.values]
            if DEBUG:
                print(f"[DEBUG] ArrayStr '{node.name}' = {values}")
            arrays_str[node.name] = values
        elif isinstance(node, Get):
            if node.array_name in arrays:
                arr = arrays[node.array_name]
            elif node.array_name in arrays_str:
                arr = arrays_str[node.array_name]
            else:
                raise NameError(f"No array named: {node.array_name}")
            index = int(eval_expr(node.index))
            if index < 0 or index >= len(arr):
                raise IndexError(f"Invalid index: {index}")
            value = arr[index]
            if DEBUG:
                print(f"[DEBUG] Get from '{node.array_name}'[{index}] = {value}")
            if node.result_var:
                variables[node.result_var] = value
            else:
                print(value)
        elif isinstance(node, Leng):
            if node.name in arrays:
                length = len(arrays[node.name])
            elif node.name in arrays_str:
                length = len(arrays_str[node.name])
            else:
                raise NameError(f"No array named: {node.name}")
            if DEBUG:
                print(f"[DEBUG] Leng '{node.name}' = {length}")
            print(length)
        elif isinstance(node, Push):
            value = eval_expr(node.value)
            # coerce numeric-looking strings to int for numeric arrays
            if isinstance(value, str) and value.replace('-', '').isdigit():
                value = int(value)
            if node.name in arrays:
                arrays[node.name].append(value)
            elif node.name in arrays_str:
                arrays_str[node.name].append(value)
            else:
                raise NameError(f"No array named: {node.name}")
            if DEBUG:
                print(f"[DEBUG] Push to '{node.name}' value = {value}")
        elif isinstance(node, Pop):
            if node.name in arrays:
                arr = arrays[node.name]
            elif node.name in arrays_str:
                arr = arrays_str[node.name]
            else:
                raise NameError(f"No array named: {node.name}")
            if arr:
                value = arr.pop()
                if DEBUG:
                    print(f"[DEBUG] Pop from '{node.name}' = {value}")
                print(value)
            else:
                raise IndexError("Empty array")

        # CONTROL FLOW
        elif isinstance(node, IfElse):
            cond_val = eval_cond(node.cond)
            if DEBUG:
                print(f"[DEBUG] If cond = {cond_val}")
            if cond_val:
                run_node(node.then_body, line_number)
            elif node.else_body:
                run_node(node.else_body, line_number)
        elif isinstance(node, WhileNode):
            iteration_count = 0
            # node.body expected to be a list of source lines (strings); runner will call run_line on each
            while eval_cond(node.cond):
                if iteration_count >= MAX_ITERATIONS:
                    raise RuntimeError(f"Line {line_number}: exceeded iteration limit ({MAX_ITERATIONS}) in while loop")
                for idx, body_line in enumerate(node.body):
                    run_line(body_line, line_number + idx + 1)
                iteration_count += 1
        elif isinstance(node, Redo):
            count = eval_expr(node.count)
            for _ in range(int(count)):
                run_node(node.action, line_number)

        # FUNCTIONS
        elif isinstance(node, Func):
            functions[node.name] = node.body
            if DEBUG:
                print(f"[DEBUG] Func defined '{node.name}'")
        elif isinstance(node, Call):
            if node.name in functions:
                if DEBUG:
                    print(f"[DEBUG] Call func '{node.name}'")
                for idx, func_line in enumerate(functions[node.name]):
                    run_line(func_line, line_number + idx + 1)
            else:
                raise NameError(f"No function named: {node.name}")

        # INPUT / FILE I/O
        elif isinstance(node, InputNode):
            prompt = eval_expr(node.prompt)
            value = input(prompt)
            if DEBUG:
                print(f"[DEBUG] Input to '{node.varname}' = {value}")
            variables[node.varname] = value
        elif isinstance(node, Write):
            text = eval_expr(node.text)
            filename = eval_expr(node.filename)
            path = os.path.join(TMP_DIR, filename)
            with open(path, "w") as f:
                f.write(str(text))
            if DEBUG:
                print(f"[DEBUG] Write to '{filename}' text = {text}")
        elif isinstance(node, Read):
            filename = eval_expr(node.filename)
            path = os.path.join(TMP_DIR, filename)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    content = f.read()
                if DEBUG:
                    print(f"[DEBUG] Read from '{filename}' = {content}")
                variables[node.varname] = content
            else:
                raise FileNotFoundError(f"No file named: {filename}")

        # TIME / DATE
        elif isinstance(node, TimeNode):
            value = int(time.time())
            print(value)
        elif isinstance(node, DateNode):
            value = datetime.now().strftime("%Y-%m-%d")
            print(value)
        elif isinstance(node, DateTimeNode):
            value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(value)
        elif isinstance(node, Sleep):
            seconds = eval_expr(node.seconds)
            time.sleep(seconds)

        # RANDOM
        elif isinstance(node, RandomNode):
            start = eval_expr(node.start)
            end = eval_expr(node.end)
            if start > end:
                raise ValueError("Start greater than end in random")
            value = random.randint(int(start), int(end))
            variables[node.varname] = value
            if DEBUG:
                print(f"[DEBUG] Random '{node.varname}' = {value}")

        # END / EXPRESSIONS
        elif isinstance(node, End):
            stop_program = True
        elif isinstance(node, BinOp) or isinstance(node, Number) or isinstance(node, Var):
            value = eval_expr(node)
            if DEBUG:
                print(f"[DEBUG] Expr value = {value}")
            print(value)
        else:
            raise TypeError(f"Unknown node type: {type(node)}")

    except Exception as e:
        print(f"[ERROR] Line {line_number}: {e}")


def run_line(line, line_number=0):
    """
    Execute a single source line. Handles semicolon-separated substatements and
    ignores blank/comment lines. Tokenizes, parses and dispatches to run_node.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if ';' in line:
        for subline in line.split(';'):
            run_line(subline.strip(), line_number)
        return
    if DEBUG:
        print(f"[DEBUG] Running line {line_number}: {line}")

    tokens = tokenize(line)
    if DEBUG:
        print(f"[DEBUG] Tokens for line {line_number}: {[f'{t.type}:{t.value}' for t in tokens]}")

    parser = Parser(tokens, line_number)
    node = parser.parse()
    run_node(node, line_number)


def run_file(filename):
    """
    Read and execute a .w source file. Supports top-level func/while blocks
    terminated by 'done'. Functions are defined and stored for later calls.
    """
    with open(filename, "r") as f:
        lines = f.readlines()
    line_number = 1
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            line_number += 1
            continue
        # function definition handling: func <name> ... done
        if line.startswith("func "):
            try:
                func_line = line[5:].strip()
                tokens = tokenize(func_line)
                parser = Parser(tokens, line_number)
                func = parser.parse_func()
                body = []
                i += 1
                line_number += 1
                while i < len(lines):
                    stripped_line = lines[i].strip()
                    if stripped_line.startswith("done"):
                        break
                    if stripped_line:
                        body.append(stripped_line)
                    i += 1
                    line_number += 1
                if i >= len(lines):
                    print(f"[ERROR] Line {line_number}: missing 'done' for function '{func.name}'")
                    i += 1
                    continue
                func.body = body
                run_node(func, line_number)
                i += 1
                line_number += 1
            except Exception as e:
                print(f"[ERROR] Line {line_number}: error in function definition: {e}")
                i += 1
                line_number += 1
                continue
        # while block handling: while <cond> ... done
        elif line.startswith("while "):
            try:
                while_line = line[6:].strip()
                tokens = tokenize(while_line)
                parser = Parser(tokens, line_number)
                whl = parser.parse_while()
                body = []
                i += 1
                line_number += 1
                start_line = line_number
                while i < len(lines):
                    stripped_line = lines[i].strip()
                    if stripped_line.startswith("done"):
                        break
                    if stripped_line:
                        body.append(stripped_line)
                    i += 1
                    line_number += 1
                if i >= len(lines):
                    print(f"[ERROR] Line {line_number}: missing 'done' for while loop")
                    i += 1
                    continue
                whl.body = body
                run_node(whl, start_line)
                i += 1
                line_number += 1
            except Exception as e:
                print(f"[ERROR] Line {line_number}: error in while loop: {e}")
                i += 1
                line_number += 1
                continue
        else:
            run_line(line, line_number)
            i += 1
            line_number += 1


# ---------------------------
# GUI / MANUAL file selection helpers
# ---------------------------
def pick_program_file_gui():
    """
    Open a small Tk file dialog to pick a .w file. Returns path or None.
    GUI is minimal; it may fail on headless systems (caught and returns None).
    """
    try:
        root = Tk()
        root.withdraw()
        root.lift()
        root.attributes("-topmost", True)
        chosen = filedialog.askopenfilename(title="W – choose .w file",
                                            filetypes=[("W scripts", "*.w"), ("All files", "*.*")])
        root.destroy()
        if chosen and os.path.isfile(chosen):
            return chosen
    except Exception:
        pass
    return None


def pick_program_file_manual():
    chosen = input("Enter path to .w file: ").strip()
    if os.path.isfile(chosen):
        return chosen
    return None


# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    if DEBUG:
        PROGRAM_FILE = "test.w" # set a default test file in debug mode  if needed change it
        if os.path.isfile(PROGRAM_FILE):
            print(f"[INFO] Running file: {PROGRAM_FILE} with DEBUG = {DEBUG}")
            run_file(PROGRAM_FILE)
        else:
            print(f"[ERROR] File not found: {PROGRAM_FILE}")
    else:
        print("Choose mode:")
        print("1 - REPL (interactive)")
        print("2 - GUI / choose a .w file")
        print("3 - Enter file path manually")
        choice = input("Choice: ").strip()
        if choice == "1":
            line_number = 1
            while True:
                try:
                    line = input(">>> ")
                    if line.lower() == "exit":
                        break
                    run_line(line, line_number)
                    line_number += 1
                except KeyboardInterrupt:
                    print("\n[REPL] interrupted")
        elif choice == "2":
            PROGRAM_FILE = pick_program_file_gui()
            if PROGRAM_FILE:
                print(f"[INFO] Selected file: {PROGRAM_FILE}")
                run_file(PROGRAM_FILE)
            else:
                print("No file selected.")
        elif choice == "3":
            PROGRAM_FILE = pick_program_file_manual()
            if PROGRAM_FILE:
                print(f"[INFO] Selected file: {PROGRAM_FILE}")
                run_file(PROGRAM_FILE)
            else:
                print("Invalid path.")
        else:
            print("Unknown choice. Exiting.")
