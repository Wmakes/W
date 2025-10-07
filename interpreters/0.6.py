import os
import random
import tempfile
import time
import math
from datetime import datetime
from tkinter import Tk, filedialog

TMP_DIR = tempfile.gettempdir()

# --- GLOBALS ---
variables = {}
arrays = {}
functions = {}
program_counter = 0
lines = []
stop_program = False
call_stack = []

# --- FILE PICKERS ---
def pick_program_file_gui():
    try:
        root = Tk()
        root.withdraw()
        root.lift()
        root.attributes("-topmost", True)
        filetypes = [("W scripts", "*.w"), ("All files", "*.*")]
        chosen = filedialog.askopenfilename(title="W – select .w file", filetypes=filetypes)
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

# --- COMMANDS ---
def cmd_show(args):
    args = args.strip()
    if args.startswith('"') and args.endswith('"'):
        print(args[1:-1])
    elif args.startswith("'") and args.endswith("'"):
        name = args[1:-1]
        if name in variables:
            print(variables[name])
        elif name in arrays:
            print(arrays[name])
        else:
            print(f"[ERROR] No variable/array: {name}")
    else:
        print(f"[ERROR] show: invalid argument → {args}")

def cmd_int(args):
    parts = args.split("'")
    if len(parts) == 3:
        value = parts[0].strip()
        name = parts[1]
        try:
            variables[name] = int(value)
        except ValueError:
            print(f"[ERROR] int: invalid number → {value}")
    else:
        print("[ERROR] Invalid int syntax")

def cmd_array(args):
    parts = args.split("'")
    if len(parts) == 3:
        values = parts[0].strip().split(',')
        name = parts[1]
        try:
            arrays[name] = [int(v.strip()) for v in values]
        except ValueError:
            print(f"[ERROR] array: invalid values → {parts[0]}")
    else:
        print("[ERROR] Invalid array syntax")

def cmd_math(expr):
    try:
        left, right = expr.split("=")
        result = eval(left.strip(), {}, variables)
        name = right.strip().strip("'")
        variables[name] = result
    except Exception as e:
        print(f"[ERROR] Invalid math operation: {expr} ({e})")

def cmd_random(args):
    try:
        parts = args.split("=")
        rng = parts[0].strip().split()
        start = int(rng[0])
        end = int(rng[1])
        varname = parts[1].strip().strip("'")
        variables[varname] = random.randint(start, end)
    except Exception as e:
        print(f"[ERROR] random: {args} ({e})")

def cmd_if(expr):
    try:
        parts = expr.split("else")
        cond_part = parts[0].strip()
        else_part = parts[1].strip() if len(parts) > 1 else None

        # condition type: int 'x' > 3
        tokens = cond_part.split()
        if tokens[0] == "int":
            varname = tokens[1].strip("'")
            op = tokens[2]
            val = int(tokens[3])
            var_val = variables.get(varname, None)
            if var_val is None:
                condition = False
            else:
                if op == ">":
                    condition = var_val > val
                elif op == "<":
                    condition = var_val < val
                elif op == "=":
                    condition = var_val == val
                else:
                    condition = False
        else:
            condition = False

        if condition:
            # remove first 4 tokens, left with action
            action = " ".join(tokens[4:])
            run_line(action)
        elif else_part:
            run_line(else_part)

    except Exception as e:
        print(f"[ERROR] Invalid if syntax: {expr} ({e})")

def cmd_redo(expr):
    try:
        count, action = expr.split(" ", 1)
        for _ in range(int(count)):
            run_line(action)
    except Exception as e:
        print(f"[ERROR] Invalid redo syntax: {expr} ({e})")

def cmd_leng(args):
    name = args.strip().strip("'")
    if name in arrays:
        print(len(arrays[name]))
    else:
        print(f"[ERROR] No array: {name}")

def cmd_push(args):
    parts = args.split()
    name = parts[0].strip("'")
    value = int(parts[1])
    if name in arrays:
        arrays[name].append(value)
    else:
        print(f"[ERROR] No array: {name}")

def cmd_pop(args):
    name = args.strip().strip("'")
    if name in arrays:
        if arrays[name]:
            print(arrays[name].pop())
        else:
            print(f"[ERROR] Empty array: {name}")
    else:
        print(f"[ERROR] No array: {name}")

def cmd_func(args):
    name = args.strip().strip('"')
    body = []
    global program_counter
    program_counter += 1
    while program_counter < len(lines) and lines[program_counter].strip() != "done":
        body.append(lines[program_counter].strip())
        program_counter += 1
    functions[name] = body

def cmd_call(args):
    name = args.strip().strip('"')
    global program_counter
    if name in functions:
        call_stack.append(program_counter)
        for line in functions[name]:
            run_line(line)
        program_counter = call_stack.pop()
    else:
        print(f"[ERROR] No function: {name}")

def cmd_input(args):
    try:
        text, var_part = args.split("=")
        text = text.strip().strip('"')
        varname = var_part.strip().strip("'")
        value = input(text + " ")
        variables[varname] = value
    except Exception as e:
        print(f"[ERROR] input: {args} ({e})")

def cmd_time():
    print(int(time.time()))

def cmd_date():
    print(datetime.now().strftime("%Y-%m-%d"))

def cmd_datetime():
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def cmd_sleep(args):
    try:
        seconds = int(args.strip())
        time.sleep(seconds)
    except Exception as e:
        print(f"[ERROR] sleep: {args} ({e})")

def cmd_write(args):
    parts = args.split('"')
    if len(parts) == 3:
        text = parts[1]
        filename = parts[2].strip()
        with open(os.path.join(TMP_DIR, filename), "w") as f:
            f.write(text)
    else:
        print("[ERROR] Invalid write syntax")

def cmd_read(args):
    parts = args.split("=")
    if len(parts) == 2:
        filename = parts[0].strip().strip('"')
        varname = parts[1].strip().strip("'")
        try:
            with open(os.path.join(TMP_DIR, filename), "r") as f:
                variables[varname] = f.read().strip()
        except Exception as e:
            print(f"[ERROR] read: {filename} ({e})")
    else:
        print("[ERROR] Invalid read syntax")

def run_line(line):
    global stop_program
    global program_counter
    if stop_program:
        return
    if line.startswith("#") or line.strip() == "":
        return
    if line.startswith("show "):
        cmd_show(line[5:].strip())
    elif line.startswith("int "):
        cmd_int(line[4:].strip())
    elif line.startswith("array "):
        cmd_array(line[6:].strip())
    elif "+" in line or "-" in line or "*" in line or "/" in line:
        cmd_math(line.strip())
    elif line.startswith("if "):
        cmd_if(line[3:].strip())
    elif line.startswith("redo "):
        cmd_redo(line[5:].strip())
    elif line.startswith("leng "):
        cmd_leng(line[5:].strip())
    elif line.startswith("push "):
        cmd_push(line[5:].strip())
    elif line.startswith("pop "):
        cmd_pop(line[4:].strip())
    elif line.startswith("func "):
        cmd_func(line[5:].strip())
    elif line.startswith("call "):
        cmd_call(line[5:].strip())
    elif line.startswith("input "):
        cmd_input(line[6:].strip())
    elif line.startswith("random "):
        cmd_random(line[7:].strip())
    elif line.startswith("write "):
        cmd_write(line[6:].strip())
    elif line.startswith("read "):
        cmd_read(line[5:].strip())
    elif line.startswith("sleep "):
        cmd_sleep(line[6:].strip())
    elif line == "time":
        cmd_time()
    elif line == "date":
        cmd_date()
    elif line == "datetime":
        cmd_datetime()
    elif line == "END":
        stop_program = True
    elif "+" in line or "-" in line or "*" in line or "/":
        cmd_math(line.strip())
    else:
        print(f"[ERROR] Unknown command: {line}")

# --- RUN FILE ---
def run_file(filename):
    global lines, program_counter
    with open(filename, "r") as f:
        lines = f.readlines()
    program_counter = 0
    while program_counter < len(lines):
        run_line(lines[program_counter].strip())
        program_counter += 1

# --- REPL ---
def repl():
    print("W REPL – enter commands, 'exit' to quit")
    while True:
        try:
            line = input(">>> ").strip()
            if line.lower() == "exit":
                break
            run_line(line)
        except KeyboardInterrupt:
            print("\n[REPL] interrupted")

# --- START ---
if __name__ == "__main__":
    print("W Interpreter 0.6")
    print("Choose mode:")
    print("1 – REPL (interactive)")
    print("2 – GUI / select .w file")
    print("3 – Enter path to file manually")

    choice = input("Choice: ").strip()
    if choice == "1":
        repl()
    elif choice == "2":
        PROGRAM_FILE = pick_program_file_gui()
        if not PROGRAM_FILE:
            print("No file selected. Exiting.")
        else:
            run_file(PROGRAM_FILE)
    elif choice == "3":
        PROGRAM_FILE = pick_program_file_manual()
        if not PROGRAM_FILE:
            print("Invalid path. Exiting.")
        else:
            run_file(PROGRAM_FILE)
    else:
        print("Unknown choice. Exiting.")
