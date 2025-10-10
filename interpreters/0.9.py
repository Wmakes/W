import os
import random
import tempfile
import time
import re
import sys
from datetime import datetime
from tkinter import filedialog, Tk

TMP_DIR = tempfile.gettempdir()
print(f"[INFO] Temp Dir: {TMP_DIR}")
DEBUG = False

# ---------------------------
# LEXER / TOKENIZER
# ---------------------------

TOKEN_SPEC = [
    ("TRUE", r"true"),
    ("FALSE", r"false"),
    ("NOT", r"not"),  # <-- added (before ID)
    ("OP", r"[\+\-\*/=<>!&|]+"),
    ("NUMBER", r"\d+(\.\d+)?"),
    ("STRING", r'"[^"]*"'),
    ("VAR", r'\'[^\']*\''),
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

class Array:
    def __init__(self, values, name):
        self.values = values
        self.name = name

class ArrayStr:
    def __init__(self, values, name):
        self.values = values
        self.name = name

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

class Get:
    def __init__(self, name, index, assign_to=None):
        self.name = name
        self.index = index
        self.assign_to = assign_to

class RandomNode:
    def __init__(self, start, end, name):
        self.start = start
        self.end = end
        self.name = name

class InputNode:
    def __init__(self, text, name):
        self.text = text
        self.name = name

class Show:
    def __init__(self, expr):
        self.expr = expr

class IfNode:
    def __init__(self, cond, then, else_):
        self.cond = cond
        self.then = then
        self.else_ = else_

class FuncNode:
    def __init__(self, name, body):
        self.name = name
        self.body = body

class CallNode:
    def __init__(self, name):
        self.name = name

class WhileNode:
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

class WriteNode:
    def __init__(self, text, filename):
        self.text = text
        self.filename = filename

class ReadNode:
    def __init__(self, filename, name):
        self.filename = filename
        self.name = name

class SleepNode:
    def __init__(self, seconds):
        self.seconds = seconds

# ---------------------------
# PARSER
# ---------------------------
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, typ):
        tok = self.current()
        if tok and tok.type == typ:
            self.pos += 1
            return tok
        else:
            raise SyntaxError(f"Expected {typ}, got {tok.type if tok else 'EOF'}")

    def parse_expr(self):
        left = self.parse_term()
        while self.current() and self.current().type == "OP" and \
                self.current().value in ("+", "-", "&&", "||", "<", ">", "=="):
            op = self.eat("OP").value
            right = self.parse_term()
            left = BinOp(left, op, right)
        return left

    def parse_term(self):
        left = self.parse_factor()
        while self.current() and self.current().type == "OP" and self.current().value in ("*", "/"):
            op = self.eat("OP").value
            right = self.parse_factor()
            left = BinOp(left, op, right)
        return left

    def parse_factor(self):
        tok = self.current()
        if tok.type == "NUMBER":
            return Number(self.eat("NUMBER").value)
        elif tok.type == "STRING":
            return StringNode(self.eat("STRING").value)
        elif tok.type == "TRUE" or tok.type == "FALSE":
            return BoolNode(self.eat(tok.type).value)
        elif tok.type == "VAR":
            return Var(self.eat("VAR").value)
        elif tok.type == "NOT":
            self.eat("NOT")
            return NotOp(self.parse_factor())
        elif tok.type == "OP" and tok.value == "-":
            self.eat("OP")
            return BinOp(Number(0), "-", self.parse_factor())
        else:
            raise SyntaxError(f"Unexpected token: {tok.type}")

    def parse_assign(self):
        expr = self.parse_expr()
        if self.current() and self.current().type == "OP" and self.current().value == "=":
            self.eat("OP")
            name = self.eat("VAR").value.strip("'")
            return Assign(name, expr)
        return expr

    def parse_bool(self):
        self.eat("ID")  # eat 'bool'
        value_tok = self.eat("TRUE") if self.current().type == "TRUE" else self.eat("FALSE")
        value = bool(value_tok.value)
        name = self.eat("VAR").value.strip("'")
        return BoolAssign(name, value)

    def parse_show(self):
        self.eat("ID")  # eat 'show'
        expr = self.parse_expr()
        return Show(expr)

    def parse_int(self):
        self.eat("ID")  # eat 'int'
        value = self.parse_expr()
        name = self.eat("VAR").value.strip("'")
        return Assign(name, value)

    def parse_array(self):
        self.eat("ID")  # eat 'array'
        values = []
        while self.current() and self.current().type in ("NUMBER", "OP"):
            if self.current().type == "OP" and self.current().value == "-":
                self.eat("OP")
                neg_value = self.parse_factor()
                values.append(BinOp(Number(0), "-", neg_value))
            else:
                values.append(self.parse_expr())
            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
        name = self.parse_expr()
        return Array(values, name)

    def parse_array_str(self):
        self.eat("ID")  # eat 'array_str'
        values = []
        while self.current() and self.current().type == "STRING":
            values.append(self.parse_expr())
            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
        name = self.parse_expr()
        return ArrayStr(values, name)

    def parse_leng(self):
        self.eat("ID")  # eat 'leng'
        name = self.parse_expr()
        return Leng(name)

    def parse_push(self):
        self.eat("ID")  # eat 'push'
        name = self.parse_expr()
        value = self.parse_expr()
        return Push(name, value)

    def parse_pop(self):
        self.eat("ID")  # eat 'pop'
        name = self.parse_expr()
        return Pop(name)

    def parse_get(self):
        self.eat("ID")  # eat 'get'
        name = self.parse_expr()
        index = self.parse_expr()
        if self.current() and self.current().type == "OP" and self.current().value == "=":
            self.eat("OP")
            assign_to = self.parse_expr()
        else:
            assign_to = None
        return Get(name, index, assign_to)

    def parse_random(self):
        self.eat("ID")  # eat 'random'
        start = self.parse_expr()
        end = self.parse_expr()
        self.eat("OP")  # eat '='
        name = self.parse_expr()
        return RandomNode(start, end, name)

    def parse_input(self):
        self.eat("ID")  # eat 'input'
        text = self.parse_expr()
        self.eat("OP")  # eat '='
        name = self.parse_expr()
        return InputNode(text, name)

    def parse_if(self):
        self.eat("ID")  # eat 'if'
        cond = self.parse_expr()
        then = self.parse_line()  # parse then action
        if self.current() and self.current().type == "ID" and self.current().value == "else":
            self.eat("ID")
            else_ = self.parse_line()
        else:
            else_ = None
        return IfNode(cond, then, else_)

    def parse_func(self):
        self.eat("ID")  # eat 'func'
        name = self.eat("ID").value
        body = self.parse_till_done()
        return FuncNode(name, body)

    def parse_call(self):
        self.eat("ID")  # eat 'call'
        name = self.parse_expr()
        return CallNode(name)

    def parse_while(self):
        self.eat("ID")  # eat 'while'
        cond = self.parse_expr()
        body = self.parse_till_done()
        return WhileNode(cond, body)

    def parse_write(self):
        self.eat("ID")  # eat 'write'
        text = self.parse_expr()
        filename = self.parse_expr()
        return WriteNode(text, filename)

    def parse_read(self):
        self.eat("ID")  # eat 'read'
        filename = self.parse_expr()
        self.eat("OP")  # eat '='
        name = self.parse_expr()
        return ReadNode(filename, name)

    def parse_sleep(self):
        self.eat("ID")  # eat 'sleep'
        seconds = self.parse_expr()
        return SleepNode(seconds)

    def parse_line(self):
        tok = self.current()
        if tok.type == "ID":
            cmd = tok.value
            #self.eat("ID")
            if cmd == "show":
                return self.parse_show()
            elif cmd == "int":
                return self.parse_int()
            elif cmd == "bool":
                return self.parse_bool()
            elif cmd == "array":
                return self.parse_array()
            elif cmd == "array_str":
                return self.parse_array_str()
            elif cmd == "leng":
                return self.parse_leng()
            elif cmd == "push":
                return self.parse_push()
            elif cmd == "pop":
                return self.parse_pop()
            elif cmd == "get":
                return self.parse_get()
            elif cmd == "random":
                return self.parse_random()
            elif cmd == "input":
                return self.parse_input()
            elif cmd == "if":
                return self.parse_if()
            elif cmd == "func":
                return self.parse_func()
            elif cmd == "call":
                return self.parse_call()
            elif cmd == "while":
                return self.parse_while()
            elif cmd == "write":
                return self.parse_write()
            elif cmd == "read":
                return self.parse_read()
            elif cmd == "sleep":
                return self.parse_sleep()
            elif cmd == "time":
                return Show(Number(int(time.time())))
            elif cmd == "date":
                return Show(StringNode(datetime.now().strftime("%Y-%m-%d")))
            elif cmd == "datetime":
                return Show(StringNode(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            elif cmd == "redo":
                raise SyntaxError("Command 'redo' is unsupported in version 0.8, use 'while'")
            else:
                raise SyntaxError(f"Unknown command: {cmd}")
        else:
            return self.parse_assign()

    def parse(self):
        nodes = []
        while self.current():
            nodes.append(self.parse_line())
            if self.current() and self.current().type == "SEMICOLON":
                self.eat("SEMICOLON")
        return nodes

    def parse_till_done(self):
        nodes = []
        while self.current() and self.current().value != 'done':
            nodes.append(self.parse_line())
        self.eat('ID')
        return nodes

# ---------------------------
# RUNTIME / EXECUTOR
# ---------------------------
variables = {}
arrays = {}
arrays_str = {}  # for string arrays
functions = {}

def run_node(node):
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
        else:
            raise NameError(f"No variable: {node.name}")
    elif isinstance(node, BinOp):
        left = run_node(node.left)
        right = run_node(node.right)
        if node.op == "+":
            return left + right
        elif node.op == "-":
            return left - right
        elif node.op == "*":
            return left * right
        elif node.op == "/":
            return left // right if isinstance(left, int) and isinstance(right, int) else left / right
        elif node.op == ">":
            return left > right
        elif node.op == "<":
            return left < right
        elif node.op == "==":
            return left == right
        elif node.op == "&&":
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise TypeError("Operator && requires boolean values")
            return left and right
        elif node.op == "||":
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise TypeError("Operator || requires boolean values")
            return left or right
        else:
            raise ValueError(f"Unknown operator: {node.op}")
    elif isinstance(node, NotOp):
        expr = run_node(node.expr)
        if not isinstance(expr, bool):
            raise TypeError("Operator not requires boolean value")
        return not expr
    elif isinstance(node, Assign):
        value = run_node(node.expr)
        variables[node.name] = value
    elif isinstance(node, BoolAssign):
        variables[node.name] = node.value
    elif isinstance(node, Show):
        value = run_node(node.expr)
        print(value)
    elif isinstance(node, Array):
        values = [run_node(v) for v in node.values]
        arrays[node.name] = values
    elif isinstance(node, ArrayStr):
        values = [run_node(v) for v in node.values]
        arrays_str[node.name] = values
    elif isinstance(node, Leng):
        name = run_node(node.name)
        if name in arrays:
            print(len(arrays[name]))
        elif name in arrays_str:
            print(len(arrays_str[name]))
        else:
            raise NameError(f"No array: {name}")
    elif isinstance(node, Push):
        name = run_node(node.name)
        value = run_node(node.value)
        if name in arrays:
            arrays[name].append(value)
        elif name in arrays_str:
            arrays_str[name].append(value)
        else:
            raise NameError(f"No array: {name}")
    elif isinstance(node, Pop):
        name = run_node(node.name)
        if name in arrays:
            if arrays[name]:
                print(arrays[name].pop())
            else:
                raise IndexError(f"Empty array: {name}")
        elif name in arrays_str:
            if arrays_str[name]:
                print(arrays_str[name].pop())
            else:
                raise IndexError(f"Empty array: {name}")
        else:
            raise NameError(f"No array: {name}")
    elif isinstance(node, Get):
        name = run_node(node.name)
        index = run_node(node.index)
        if index < 0:
            raise IndexError(f"Invalid index: {index}")
        if name in arrays:
            arr = arrays[name]
        elif name in arrays_str:
            arr = arrays_str[name]
        else:
            raise NameError(f"No array: {name}")
        if index >= len(arr):
            raise IndexError(f"Invalid index: {index}")
        value = arr[index]
        if node.assign_to:
            variables[run_node(node.assign_to)] = value
        else:
            print(value)
    elif isinstance(node, RandomNode):
        start = run_node(node.start)
        end = run_node(node.end)
        name = run_node(node.name)
        variables[name] = random.randint(start, end)
    elif isinstance(node, InputNode):
        text = run_node(node.text)
        name = run_node(node.name)
        value = input(text + " ")
        variables[name] = value
    elif isinstance(node, IfNode):
        cond = run_node(node.cond)
        if cond:
            run_node(node.then)
        elif node.else_:
            run_node(node.else_)
    elif isinstance(node, FuncNode):
        name = run_node(node.name)
        functions[name] = node.body
    elif isinstance(node, CallNode):
        name = run_node(node.name)
        if name in functions:
            for sub_node in functions[name]:
                run_node(sub_node)
        else:
            raise NameError(f"No function: {name}")
    elif isinstance(node, WhileNode):
        while run_node(node.cond):
            for sub_node in node.body:
                run_node(sub_node)
            
    elif isinstance(node, WriteNode):
        text = run_node(node.text)
        filename = run_node(node.filename)
        with open(os.path.join(TMP_DIR, filename), "w") as f:
            f.write(text)
    elif isinstance(node, ReadNode):
        filename = run_node(node.filename)
        name = run_node(node.name)
        with open(os.path.join(TMP_DIR, filename), "r") as f:
            variables[name] = f.read().strip()
    elif isinstance(node, SleepNode):
        seconds = run_node(node.seconds)
        time.sleep(seconds)


def run_file(filename):
    with open(filename, "r") as f:
        lines = f.readlines()

    tokens = []
    for line in lines:
        if line.startswith("#") or line.strip() == "":
            continue
        tokens += tokenize(line)

    #try:
    nodes = Parser(tokens).parse()
    for node in nodes:
        run_node(node)

    #except Exception as e:
    #    print(f"[ERROR]: {e}")


# ---------------------------
# GUI / MANUAL
# ---------------------------
def pick_program_file_gui():
    try:
        root = Tk()
        root.withdraw()
        root.lift()
        root.attributes("-topmost", True)
        chosen = filedialog.askopenfilename(title="W – select .w file", filetypes=[("W scripts", "*.w"), ("All files", "*.*")])
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
    elif len(sys.argv) > 1:
        PROGRAM_FILE = sys.argv[1]
        if PROGRAM_FILE:
            print(f"[INFO] Selected file: {PROGRAM_FILE}")
            run_file(PROGRAM_FILE)
        else:
            print("Invalid path.")
    else:
        print("Choose mode:")
        print("1 – REPL (interactive)")
        print("2 – GUI / select .w file")
        print("3 – Enter path to file manually")
        choice = input("Choice: ").strip()
        if choice == "1":
            while True:
                try:
                    line = input(">>> ")
                    if line.lower() == "exit":
                        break
                    #run_line(line) #!TODO
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
