import os
import random
import tempfile
import time
from datetime import datetime
from tkinter import filedialog, Tk

TMP_DIR = tempfile.gettempdir()
DEBUG = False

# ---------------------------
# LEXER / TOKENIZER
# ---------------------------
import re

TOKEN_SPEC = [
    ("OP",       r"[\+\-\*/=<>!&]+"),
    ("NUMBER",   r"\d+(\.\d+)?"),
    ("STRING",   r'"[^"]*"|\'[^\']*\''),
    ("ID",       r"[A-Za-z_]\w*"),
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

class Var:
    def __init__(self, name):
        self.name = name[1:-1] if name.startswith("'") or name.startswith('"') else name

class BinOp:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class Assign:
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

class Show:
    def __init__(self, expr):
        self.expr = expr

class Array:
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

class RandomNode:
    def __init__(self, start, end, name):
        self.start = start
        self.end = end
        self.name = name

class InputNode:
    def __init__(self, text, name):
        self.text = text
        self.name = name

class IfNode:
    def __init__(self, cond, then, else_):
        self.cond = cond
        self.then = then
        self.else_ = else_

class FuncNode:
    def __init__(self, name):
        self.name = name
        self.body = []

class CallNode:
    def __init__(self, name):
        self.name = name

class RedoNode:
    def __init__(self, count, action):
        self.count = count
        self.action = action

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

class WhileNode:
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

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
        while self.current() and self.current().type == "OP" and self.current().value in ("+", "-", "&"):
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
        elif tok.type == "ID":
            return Var(self.eat("ID").value)
        elif tok.type == "OP" and tok.value == "-":
            self.eat("OP")
            return BinOp(Number(0), "-", self.parse_factor())
        else:
            raise SyntaxError(f"Unexpected token: {tok.type}")

    def parse_assign(self):
        expr = self.parse_expr()
        if self.current() and self.current().type == "OP" and self.current().value == "=":
            self.eat("OP")
            name_tok = self.eat("STRING") if self.current().type == "STRING" else self.eat("ID")
            name = name_tok.value
            return Assign(name, expr)
        return expr

    def parse_show(self):
        self.eat("ID")  # eat 'show'
        expr = self.parse_expr()
        return Show(expr)

    def parse_int(self):
        self.eat("ID")  # eat 'int'
        value = self.parse_expr()
        name = self.eat("STRING").value if self.current().type == "STRING" else self.eat("ID").value
        return Assign(name, value)

    def parse_array(self):
        self.eat("ID")  # eat 'array'
        values = []
        while self.current() and self.current().type == "NUMBER":
            values.append(self.parse_expr())
            if self.current() and self.current().type == "COMMA":
                self.eat("COMMA")
        name = self.eat("STRING").value if self.current().type == "STRING" else self.eat("ID").value
        return Array(values, name)

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
        name = self.parse_expr()
        return FuncNode(name)

    def parse_call(self):
        self.eat("ID")  # eat 'call'
        name = self.parse_expr()
        return CallNode(name)

    def parse_redo(self):
        self.eat("ID")  # eat 'redo'
        count = self.parse_expr()
        action = self.parse_line()
        return RedoNode(count, action)

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

    def parse_while(self):
        self.eat("ID")  # eat 'while'
        cond = self.parse_expr()
        body = []  # body will be added later in run_file
        return WhileNode(cond, body)

    def parse_line(self):
        tok = self.current()
        if tok.type == "ID":
            cmd = tok.value
            self.eat("ID")
            if cmd == "show":
                return self.parse_show()
            elif cmd == "int":
                return self.parse_int()
            elif cmd == "array":
                return self.parse_array()
            elif cmd == "leng":
                return self.parse_leng()
            elif cmd == "push":
                return self.parse_push()
            elif cmd == "pop":
                return self.parse_pop()
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
            elif cmd == "redo":
                return self.parse_redo()
            elif cmd == "write":
                return self.parse_write()
            elif cmd == "read":
                return self.parse_read()
            elif cmd == "sleep":
                return self.parse_sleep()
            elif cmd == "while":
                return self.parse_while()
            elif cmd == "time":
                return Show(Number(int(time.time())))
            elif cmd == "date":
                return Show(StringNode(datetime.now().strftime("%Y-%m-%d")))
            elif cmd == "datetime":
                return Show(StringNode(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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

# ---------------------------
# RUNTIME / EXECUTOR
# ---------------------------
variables = {}
arrays = {}
functions = {}
while_loops = {}  # to handle while bodies

def run_node(node):
    if isinstance(node, Number):
        return node.value
    elif isinstance(node, StringNode):
        return node.value
    elif isinstance(node, Var):
        if node.name in variables:
            return variables[node.name]
        elif node.name in arrays:
            return arrays[node.name]
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
        elif node.op == "=":
            return left == right
        elif node.op == "&":
            return left and right
        else:
            raise ValueError(f"Unknown operator: {node.op}")
    elif isinstance(node, Assign):
        value = run_node(node.expr)
        variables[node.name] = value
    elif isinstance(node, Show):
        value = run_node(node.expr)
        print(value)
    elif isinstance(node, Array):
        values = [run_node(v) for v in node.values]
        arrays[node.name] = values
    elif isinstance(node, Leng):
        name = run_node(node.name)
        print(len(arrays.get(name, [])))
    elif isinstance(node, Push):
        name = run_node(node.name)
        value = run_node(node.value)
        if name in arrays:
            arrays[name].append(value)
        else:
            raise NameError(f"No array: {name}")
    elif isinstance(node, Pop):
        name = run_node(node.name)
        if name in arrays and arrays[name]:
            print(arrays[name].pop())
        else:
            raise IndexError(f"Empty or no array: {name}")
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
            for line in functions[name]:
                run_line(line, 0)  # line number 0 for functions
    elif isinstance(node, RedoNode):
        count = run_node(node.count)
        for _ in range(count):
            run_node(node.action)
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
    elif isinstance(node, WhileNode):
        while run_node(node.cond):
            for body_line in node.body:
                run_line(body_line, 0)  # line number 0 for loop body

def run_line(line, line_number=0):
    if line.startswith("#") or line.strip() == "":
        return
    if line == "done":
        return
    try:
        tokens = tokenize(line)
        parser = Parser(tokens)
        nodes = parser.parse()
        for node in nodes:
            run_node(node)
    except Exception as e:
        print(f"[ERROR] Line {line_number}: {e}")

def run_file(filename):
    with open(filename, "r") as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("func "):
            tokens = tokenize(line)
            parser = Parser(tokens)
            func = parser.parse_func()
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != "done":
                body.append(lines[i].strip())
                i += 1
            func.body = body
            run_node(func)
        elif line.startswith("while "):
            tokens = tokenize(line)
            parser = Parser(tokens)
            while_node = parser.parse_while()
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != "done":
                body.append(lines[i].strip())
                i += 1
            while_node.body = body
            run_node(while_node)
        else:
            run_line(line, i+1)
        i += 1

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
        PROGRAM_FILE = "/Kody-programów/test-all.w"  # Note: Keep for debug, but translate messages
        if os.path.isfile(PROGRAM_FILE):
            print(f"[INFO] Running file: {PROGRAM_FILE} with DEBUG = {DEBUG}")
            run_file(PROGRAM_FILE)
        else:
            print(f"[ERROR] File not found: {PROGRAM_FILE}")
    else:
        print("Choose mode:")
        print("1 – REPL (interactive)")
        print("2 – GUI / select .w file")
        print("3 – Enter path to file manually")

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
