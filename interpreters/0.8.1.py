import os
import random
import tempfile
import time
import re
from datetime import datetime
from tkinter import filedialog, Tk

TMP_DIR = tempfile.gettempdir()
DEBUG = True

# ---------------------------
# LEXER / TOKENIZER
# ---------------------------

TOKEN_SPEC = [
    ("TRUE", r"true"),
    ("FALSE", r"false"),
    ("NOT", r"not"),
    ("AND", r"and"),
    ("OR", r"or"),
    ("OP", r"[\+\-\*/=<>!]+"),
    ("NUMBER", r"\d+(\.\d+)?"),
    ("STRING", r'"[^"]*"|\'[^\']*\''),
    ("ID", r"[A-Za-z_]\w*"),
    ("NEWLINE",  r"\n"),
    ("SKIP",     r"[ \t]+"),
    ("SEMICOLON", r";"),
    ("COMMA",    r","),
    ("COMMENT",  r"#.*"),
]

TOKEN_REGEX = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
get_token = re.compile(TOKEN_REGEX).match

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

def tokenize(code):
    pos = 0
    tokens = []
    while pos < len(code):
        m = get_token(code, pos)
        if not m:
            raise SyntaxError(f"Unknown token at position {pos}: {code[pos:pos+10]}")
        typ = m.lastgroup
        val = m.group(typ)
        if typ not in ("SKIP", "NEWLINE", "COMMENT"):
            tokens.append(Token(typ, val))
        pos = m.end()
    return tokens

# ---------------------------
# AST NODES
# ---------------------------
class Number:
    def __init__(self, value):
        self.value = float(value) if '.' in str(value) else int(value)

class StringNode:
    def __init__(self, value):
        self.value = value[1:-1]

class BoolNode:
    def __init__(self, value):
        self.value = value == "true"

class Var:
    def __init__(self, name):
        self.name = name[1:-1] if name.startswith("'") or name.startswith('"') else name

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
        raise SyntaxError(f"Error in line {self.line_number}: Expected {typ}, got {token.type if token else 'end'}")

    def parse(self):
        return self.parse_stmt()

    def parse_stmt(self):
        token = self.current()
        if not token:
            return None
        if token.type == 'ID':
            cmd = self.eat('ID')
            if cmd == 'show':
                return self.parse_show()
            elif cmd == 'int':
                return self.parse_int()
            elif cmd == 'bool':
                return self.parse_bool()
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
            elif cmd == 'random':
                return self.parse_random()
            elif cmd == 'write':
                return self.parse_write()
            elif cmd == 'read':
                return self.parse_read()
            elif cmd == 'sleep':
                return self.parse_sleep()
            elif cmd in ('time', 'date', 'datetime'):
                node_map = {'time': TimeNode, 'date': DateNode, 'datetime': DateTimeNode}
                return node_map[cmd]()
            elif cmd == 'END':
                return End()
            else:
                self.pos -= 1
                return self.parse_math()
        else:
            return self.parse_math()

    def parse_show(self):
        expr = self.parse_expr()
        return Show(expr)

    def parse_int(self):
        sign = 1
        if self.current() and self.current().type == 'OP' and self.current().value == '-':
            self.eat('OP')
            sign = -1
        val = self.eat('NUMBER')
        num = Number(val)
        num.value = sign * num.value
        name = self.eat('STRING')
        return Assign(name[1:-1], num)

    def parse_bool(self):
        token = self.current()
        if token and token.type in ('TRUE', 'FALSE'):
            val = self.eat(token.type)
            name = self.eat('STRING')
            return BoolAssign(name[1:-1], val)
        raise SyntaxError(
            f"Error in line {self.line_number}: Expected 'true' or 'false', got {token.value if token else 'end'}")

    def parse_array(self):
        values = []
        while self.current() and (self.current().type == 'NUMBER' or (self.current().type == 'OP' and self.current().value == '-')):
            sign = 1
            if self.current().type == 'OP' and self.current().value == '-':
                self.eat('OP')
                sign = -1
            val = self.eat('NUMBER')
            num = Number(val)
            num.value = sign * num.value
            values.append(num)
            if self.current() and self.current().type == 'COMMA':
                self.eat('COMMA')
        name = self.eat('STRING')
        return Array(values, name[1:-1])

    def parse_array_str(self):
        elements = []
        while True:
            token = self.current()
            if token is None or token.type != 'STRING':
                raise SyntaxError(f"Error in line {self.line_number}: Expected STRING after 'array_str'")
            elements.append(token.value.strip('"\''))
            self.eat('STRING')
            if self.current() and self.current().type == 'COMMA':
                self.eat('COMMA')
                continue
            break
        name = self.eat('STRING')[1:-1]  # Remove quotes from array name
        return ArrayStr(elements, name)

    def parse_get(self):
        array_name = self.eat('STRING')[1:-1]
        index = self.parse_expr()
        result_var = None
        if self.current() and self.current().type == 'OP' and self.current().value == '=':
            self.eat('OP')
            result_var = self.eat('STRING')[1:-1]
        return Get(array_name, index, result_var)

    def parse_leng(self):
        name = self.eat('STRING')
        return Leng(name[1:-1])

    def parse_push(self):
        name = self.eat('STRING')
        value = self.parse_expr()
        return Push(name[1:-1], value)

    def parse_pop(self):
        name = self.eat('STRING')
        return Pop(name[1:-1])

    def parse_if(self):
        cond = self.parse_condition()
        action_true = self.parse_stmt()
        action_false = None
        if self.current() and self.current().value == 'else':
            self.eat('ID')
            action_false = self.parse_stmt()
        return IfElse(cond, action_true, action_false)

    def parse_while(self):
        cond = self.parse_condition()
        return WhileNode(cond, [])

    def parse_condition(self):
        left = self.parse_comp()
        while self.current() and self.current().type in ('AND', 'OR'):
            op = self.eat(self.current().type)
            right = self.parse_comp()
            left = BinOp(left, op, right)
        return left

    def parse_comp(self):
        token = self.current()
        if token and token.type == 'NOT':
            self.eat('NOT')
            expr = self.parse_comp()
            return NotOp(expr)
        left = self.parse_expr()
        token = self.current()
        if token and token.type == 'OP' and token.value in ('=', '!=', '>', '<', '>=', '<='):
            op = self.eat('OP')
            right = self.parse_expr()
            return Cond(left, op, right)
        return left

    def parse_redo(self):
        print(f"[DEPRECATION] Line {self.line_number}: redo is deprecated, use while")
        sign = 1
        if self.current() and self.current().type == 'OP' and self.current().value == '-':
            self.eat('OP')
            sign = -1
        count_val = self.eat('NUMBER')
        count = Number(count_val)
        count.value = sign * count.value
        action = self.parse_stmt()
        return Redo(count, action)

    def parse_func(self):
        name = self.eat('STRING')
        return Func(name[1:-1], [])

    def parse_call(self):
        name = self.eat('STRING')
        return Call(name[1:-1])

    def parse_input(self):
        prompt = self.eat('STRING')[1:-1]
        self.eat('OP')
        varname = self.eat('STRING')[1:-1]
        return InputNode(prompt, varname)

    def parse_random(self):
        sign1 = 1
        if self.current() and self.current().type == 'OP' and self.current().value == '-':
            self.eat('OP')
            sign1 = -1
        start_val = self.eat('NUMBER')
        start = Number(start_val)
        start.value = sign1 * start.value
        sign2 = 1
        if self.current() and self.current().type == 'OP' and self.current().value == '-':
            self.eat('OP')
            sign2 = -1
        end_val = self.eat('NUMBER')
        end = Number(end_val)
        end.value = sign2 * end.value
        self.eat('OP')
        varname = self.eat('STRING')[1:-1]
        return RandomNode(start, end, varname)

    def parse_write(self):
        text = self.eat('STRING')[1:-1]
        filename = self.eat('STRING')[1:-1]
        return Write(text, filename)

    def parse_read(self):
        filename = self.eat('STRING')[1:-1]
        varname = self.eat('STRING')[1:-1]
        return Read(filename, varname)

    def parse_sleep(self):
        sign = 1
        if self.current() and self.current().type == 'OP' and self.current().value == '-':
            self.eat('OP')
            sign = -1
        seconds_val = self.eat('NUMBER')
        seconds = Number(seconds_val)
        seconds.value = sign * seconds.value
        return Sleep(seconds)

    def parse_math(self):
        left = self.parse_expr()
        if self.current() and self.current().type == 'OP' and self.current().value == '=':
            self.eat('OP')
            token = self.current()
            if token and token.type in ('STRING', 'ID'):
                name_token = self.eat(token.type)
                name = name_token[1:-1] if token.type == 'STRING' else name_token
                return Assign(name, left)
            else:
                raise SyntaxError(f"Error in line {self.line_number}: expected variable name after '='")
        return left

    def parse_expr(self):
        left = self.parse_term()
        while self.current() and self.current().type in ('OP', 'AND', 'OR') and self.current().value in ('+', '-',
                                                                                                         'and', 'or'):
            op = self.eat(self.current().type)
            right = self.parse_term()
            left = BinOp(left, op, right)
        return left

    def parse_term(self):
        left = self.parse_factor()
        while self.current() and self.current().type == 'OP' and self.current().value in ('*', '/'):
            op = self.eat('OP')
            right = self.parse_factor()
            left = BinOp(left, op, right)
        return left

    def parse_factor(self):
        token = self.current()
        if token.type == 'OP' and token.value == '-':
            self.eat('OP')
            factor = self.parse_factor()
            if isinstance(factor, Number):
                factor.value = -factor.value
                return factor
            return BinOp(Number(0), '-', factor)
        elif token.type == 'NOT':
            self.eat('NOT')
            expr = self.parse_factor()
            return NotOp(expr)
        elif token.type == 'NUMBER':
            self.eat('NUMBER')
            return Number(token.value)
        elif token.type == 'STRING':
            self.eat('STRING')
            if token.value.startswith("'"):
                return Var(token.value)
            else:
                return StringNode(token.value)
        elif token.type == 'TRUE':
            self.eat('TRUE')
            return BoolNode("true")
        elif token.type == 'FALSE':
            self.eat('FALSE')
            return BoolNode("false")
        elif token.type == 'ID':
            self.eat('ID')
            return Var(token.value)
        raise SyntaxError(f"Error in line {self.line_number}: Expected number, string, bool or var")

# ---------------------------
# INTERPRETER
# ---------------------------
variables = {}
arrays = {}
functions = {}
stop_program = False

def eval_expr(expr, line_number):
    if isinstance(expr, Number):
        return expr.value
    elif isinstance(expr, StringNode):
        return expr.value
    elif isinstance(expr, BoolNode):
        return expr.value
    elif isinstance(expr, Var):
        name = expr.name
        if name in variables:
            return variables[name]
        elif name in arrays:
            return arrays[name]
        raise ValueError(f"Line {line_number}: No such variable/array: {name}")
    elif isinstance(expr, BinOp):
        left = eval_expr(expr.left, line_number)
        right = eval_expr(expr.right, line_number)
        if expr.op == '+':
            return left + right
        elif expr.op == '-':
            return left - right
        elif expr.op == '*':
            return left * right
        elif expr.op == '/':
            if right == 0:
                raise ValueError(f"Line {line_number}: Division by zero")
            return left / right
        elif expr.op == 'and':
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise ValueError(f"Line {line_number}: Operator and requires logical values")
            return left and right
        elif expr.op == 'or':
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise ValueError(f"Line {line_number}: Operator or requires logical values")
            return left or right
        raise ValueError(f"Line {line_number}: Unknown operator: {expr.op}")
    elif isinstance(expr, NotOp):
        value = eval_expr(expr.expr, line_number)
        if not isinstance(value, bool):
            raise ValueError(f"Line {line_number}: Operator not requires a logical value")
        return not value
    raise ValueError(f"Line {line_number}: Unknown expression")

def eval_cond(cond, line_number):
    if isinstance(cond, NotOp):
        value = eval_cond(cond.expr, line_number)
        if not isinstance(value, bool):
            raise ValueError(f"Line {line_number}: Operator not requires a logical value")
        return not value
    elif isinstance(cond, BinOp):
        left = eval_cond(cond.left, line_number)
        right = eval_cond(cond.right, line_number)
        if cond.op == 'and':
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise ValueError(f"Line {line_number}: Operator and requires logical values")
            return left and right
        elif cond.op == 'or':
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise ValueError(f"Line {line_number}: Operator or requires logical values")
            return left or right
        else:
            raise ValueError(f"Line {line_number}: Unknown logical operator: {cond.op}")
    elif isinstance(cond, Cond):
        left = eval_expr(cond.left, line_number)
        right = eval_expr(cond.right, line_number)
        op = cond.op
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
        else:
            raise ValueError(f"Line {line_number}: Unknown conditional operator: {op}")
    else:
        value = eval_expr(cond, line_number)
        if not isinstance(value, bool):
            raise ValueError(f"Line {line_number}: Condition must be a logical value, got {type(value)}")
        return value

def run_node(node, line_number):
    global stop_program, DEBUG
    if node is None or stop_program:
        return
    MAX_LOOP_ITERS = 100000000000
    try:
        if isinstance(node, Show):
            print(eval_expr(node.expr, line_number))
        elif isinstance(node, Assign):
            variables[node.name] = eval_expr(node.expr, line_number)
            if DEBUG:
                print(f"[DEBUG] Line {line_number}: Assigned '{node.name}' = {variables[node.name]}")
        elif isinstance(node, BoolAssign):
            variables[node.name] = node.value == "true"
            if DEBUG:
                print(f"[DEBUG] Line {line_number}: Assigned '{node.name}' = {variables[node.name]}")
        elif isinstance(node, Array):
            arrays[node.name] = [eval_expr(v, line_number) for v in node.values]
        elif isinstance(node, ArrayStr):
            arrays[node.name] = node.values
        elif isinstance(node, Get):
            if node.array_name not in arrays:
                raise ValueError(f"Line {line_number}: No such array '{node.array_name}'")
            index = eval_expr(node.index, line_number)
            if not isinstance(index, (int, float)) or int(index) != index:
                raise ValueError(f"Line {line_number}: Index must be an integer, got {index}")
            index = int(index)
            if index < 0 or index >= len(arrays[node.array_name]):
                raise ValueError(f"Line {line_number}: Invalid index {index} for array '{node.array_name}' with length {len(arrays[node.array_name])}")
            value = arrays[node.array_name][index]
            if node.result_var:
                variables[node.result_var] = value
            else:
                print(value)
        elif isinstance(node, Leng):
            if node.name not in arrays:
                raise ValueError(f"Line {line_number}: No such array '{node.name}'")
            print(len(arrays[node.name]))
        elif isinstance(node, Push):
            if node.name not in arrays:
                raise ValueError(f"Line {line_number}: No such array '{node.name}'")
            value = eval_expr(node.value, line_number)
            arrays[node.name].append(value)
        elif isinstance(node, Pop):
            if node.name not in arrays:
                raise ValueError(f"Line {line_number}: No such array '{node.name}'")
            if not arrays[node.name]:
                raise ValueError(f"Line {line_number}: Array '{node.name}' is empty")
            print(arrays[node.name].pop())
        elif isinstance(node, IfElse):
            if eval_cond(node.cond, line_number):
                run_node(node.then_body, line_number)
            elif node.else_body:
                run_node(node.else_body, line_number)
        elif isinstance(node, WhileNode):
            iters = 0
            while eval_cond(node.cond, line_number):
                for line in node.body:
                    tokens = tokenize(line)
                    parser = Parser(tokens, line_number)
                    sub_node = parser.parse()
                    run_node(sub_node, line_number)
                iters += 1
                if iters >= MAX_LOOP_ITERS:
                    raise RuntimeError(f"Line {line_number}: Exceeded maximum loop iterations ({MAX_LOOP_ITERS})")
        elif isinstance(node, Func):
            functions[node.name] = node.body
        elif isinstance(node, Call):
            if node.name in functions:
                for line in functions[node.name]:
                    tokens = tokenize(line)
                    parser = Parser(tokens, line_number)
                    sub_node = parser.parse()
                    run_node(sub_node, line_number)
            else:
                raise ValueError(f"Line {line_number}: No such function: {node.name}")
        elif isinstance(node, InputNode):
            value = input(node.prompt + " ")
            variables[node.varname] = value
        elif isinstance(node, TimeNode):
            print(int(time.time()))
        elif isinstance(node, DateNode):
            print(datetime.now().strftime("%Y-%m-%d"))
        elif isinstance(node, DateTimeNode):
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        elif isinstance(node, Sleep):
            seconds = eval_expr(node.seconds, line_number)
            if not isinstance(seconds, (int, float)):
                raise ValueError(f"Line {line_number}: sleep: expected a number")
            if seconds < 0:
                raise ValueError(f"Line {line_number}: Negative time in sleep")
            time.sleep(seconds)
        elif isinstance(node, RandomNode):
            start = eval_expr(node.start, line_number)
            end = eval_expr(node.end, line_number)
            if not (isinstance(start, (int, float)) and isinstance(end, (int, float))):
                raise ValueError(f"Line {line_number}: random: expected integers")
            if start > end:
                raise ValueError(f"Line {line_number}: Start greater than end in random")
            variables[node.varname] = random.randint(int(start), int(end))
        elif isinstance(node, Write):
            filename = os.path.basename(node.filename)
            path = os.path.join(TMP_DIR, filename)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(node.text)
            except OSError as e:
                raise ValueError(f"Line {line_number}: File write error: {e}")
        elif isinstance(node, Read):
            filename = os.path.basename(node.filename)
            path = os.path.join(TMP_DIR, filename)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    variables[node.varname] = f.read()
            else:
                variables[node.varname] = ""
                raise ValueError(f"Line {line_number}: No such file: {node.filename}")
        elif isinstance(node, End):
            stop_program = True
        elif isinstance(node, (Number, StringNode, BoolNode, Var)):
            pass
        else:
            raise ValueError(f"Line {line_number}: Unknown node type: {type(node).__name__}")
    except Exception as e:
        print(f"[ERROR] Line {line_number}: {str(e)}")
        return

def run_line(line, line_number):
    line = line.strip()
    if not line or line.startswith("#"):
        return
    tokens = tokenize(line)
    parser = Parser(tokens, line_number)
    node = parser.parse()
    run_node(node, line_number)

def run_file(filename):
    global stop_program
    stop_program = False
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    i = 0
    line_number = 1  # Change to 1 to be consistent with file line numbering
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("#"):
            i += 1
            continue
        if line.startswith("func "):
            try:
                func_line = line[5:].strip()
                tokens = tokenize(func_line)
                parser = Parser(tokens, line_number)
                func = parser.parse_func()
                body = []
                i += 1
                while i < len(lines):
                    stripped_line = lines[i].strip()
                    if stripped_line.startswith("done"):
                        break
                    if stripped_line:
                        body.append(stripped_line)
                    i += 1
                if i >= len(lines):
                    print(f"[ERROR] Line {line_number}: Missing 'done' for function '{func.name}'")
                    i += 1
                    continue
                func.body = body
                run_node(func, line_number)
                i += 1
            except Exception as e:
                print(f"[ERROR] Line {line_number}: Error in function definition: {e}")
                i += 1
                continue
        elif line.startswith("while "):
            try:
                while_line = line[6:].strip()
                tokens = tokenize(while_line)
                parser = Parser(tokens, line_number)
                whl = parser.parse_while()
                body = []
                i += 1
                while i < len(lines):
                    stripped_line = lines[i].strip()
                    if stripped_line.startswith("done"):
                        break
                    if stripped_line:
                        body.append(stripped_line)
                    i += 1
                if i >= len(lines):
                    print(f"[ERROR] Line {line_number}: Missing 'done' for while loop")
                    i += 1
                    continue
                whl.body = body
                run_node(whl, line_number)
                i += 1
            except Exception as e:
                print(f"[ERROR] Line {line_number}: Error in while loop: {e}")
                i += 1
                continue
        else:
            run_line(line, line_number)
            i += 1
        line_number += 1  # Increment after every line, even empty, for consistency

# ---------------------------
# GUI / MANUAL
# ---------------------------
def pick_program_file_gui():
    try:
        root = Tk()
        root.withdraw()
        root.lift()
        root.attributes("-topmost", True)
        chosen = filedialog.askopenfilename(title="W – choose .w file", filetypes=[("W scripts", "*.w"), ("All files", "*.*")])
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
        PROGRAM_FILE = "test.w"
        if os.path.isfile(PROGRAM_FILE):
            print(f"[INFO] Running file: {PROGRAM_FILE} with DEBUG = {DEBUG}")
            run_file(PROGRAM_FILE)
        else:
            print(f"[ERROR] File not found: {PROGRAM_FILE}")
    else:
        print("Choose mode:")
        print("1 – REPL (interactive)")
        print("2 – GUI / choose .w file")
        print("3 – Enter file path manually")
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
                print(f"[INFO] Chosen file: {PROGRAM_FILE}")
                run_file(PROGRAM_FILE)
            else:
                print("No file chosen.")
        elif choice == "3":
            PROGRAM_FILE = pick_program_file_manual()
            if PROGRAM_FILE:
                print(f"[INFO] Chosen file: {PROGRAM_FILE}")
                run_file(PROGRAM_FILE)
            else:
                print("Invalid path.")
        else:
            print("Unknown choice. Exiting.")
