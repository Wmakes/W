# interpreter.py
import sys

# Set your own PROGRAM_FILE path here!
PROGRAM_FILE = None
if PROGRAM_FILE is None:
    raise ValueError("Please set your own PROGRAM_FILE path to a .w file!")

variables = {}
arrays = {}
program_counter = 0
lines = []
stop_program = False

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
            print(f"[ERROR] No such variable/array: {name}")
    else:
        print(f"[ERROR] show: invalid argument → {args}")

def cmd_int(args):
    parts = args.split('"')
    if len(parts) == 3:
        value = parts[0].strip()
        name = parts[1]
        variables[name] = int(value)
    else:
        print("[ERROR] Invalid int syntax")

def cmd_array(args):
    parts = args.split('"')
    if len(parts) == 3:
        values = parts[0].strip().split(',')
        name = parts[1]
        arrays[name] = [int(v.strip()) for v in values]
    else:
        print("[ERROR] Invalid array syntax")

def cmd_math(expr):
    try:
        left, right = expr.split("=")
        result = eval(left.strip(), {}, variables)
        name = right.strip().strip('"')
        variables[name] = result
    except Exception as e:
        print(f"[ERROR] Invalid math operation: {expr} ({e})")

def cmd_if(expr):
    try:
        parts = expr.split("else")
        cond_part = parts[0].strip()
        else_part = parts[1].strip() if len(parts) > 1 else None

        # condition e.g.: int "x" = 3
        cond_tokens = cond_part.split()
        if cond_tokens[0] == "int":
            varname = cond_tokens[1].strip('"').strip("'")
            op = cond_tokens[2]
            val = int(cond_tokens[3])
            var_val = variables.get(varname, None)
            if var_val is None:
                condition = False
            else:
                if op == "=":
                    condition = var_val == val
                else:
                    condition = False 
        else:
            condition = False

        if condition:
            action = " ".join(cond_tokens[4:])
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

def run_line(line):
    global stop_program
    if stop_program:  # if END was earlier → stop
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
    elif line == "END":
        stop_program = True
    elif line == "break":
        return 
    else:
        print(f"[ERROR] Unknown command: {line}")

def run_file(filename):
    global lines
    with open(filename, "r") as f:
        lines = f.readlines()
    for line in lines:
        run_line(line.strip())

if __name__ == "__main__":
    run_file(PROGRAM_FILE)
