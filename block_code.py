import pygame
import random

def checkifvar(args, num, ctx):
    if num >= len(args): return 0
    val = args[num]
    
    # 1. Logic for Nested O-Blocks
    if isinstance(val, dict) and val.get("type") == "expr":
        opcode_name = val.get("opcode")
        params = val.get("params", [])
        if opcode_name in OPCODES:
            # Recursion: The O-block solves itself and returns a number/string
            return OPCODES[opcode_name](ctx, params)
        return 0

    # 2. Handle Variable Strings ("var:my_variable")
    st = str(val)
    if st.startswith("var:"):
        var_name = st[4:]
        return ctx["vars"].get(var_name, 0)
    
    # 3. Handle Type Strings ("type:my_variable")
    if st.startswith("type:"):
        var_name = st[5:]
        return type(ctx["vars"].get(var_name, 0))

    # 4. Handle Literals & Casting
    try:
        if "." in st: return float(st)
        return int(st)
    except:
        return val

# --- REPORTER OPCODES (O-Blocks) ---
# These return values to be used by other blocks.

def math_dispatcher(ctx, args):
    return float(checkifvar(args, 0, ctx)) + float(checkifvar(args, 1, ctx))

# Add the specific math functions
def op_add(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) + float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return 0 # Default to 0 if the input isn't a number
def op_sub(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) - float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return 0 # Default to 0 if the input isn't a number
def op_mul(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) * float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return 0 # Default to 0 if the input isn't a number
def op_div(ctx, args):
    try:
        d = float(checkifvar(args, 1, ctx))
        return float(checkifvar(args, 0, ctx)) / d if d != 0 else 0
    except (ValueError, TypeError):
        return 0 # Default to 0 if the input isn't a number
def op_get(ctx, args):
    # args[0] is the variable name inside the Get block's slot
    var_name = str(args[0])
    return ctx["vars"].get(var_name, 0)
def op_int(ctx, args):
    try:
        return int(float(checkifvar(args, 0, ctx)))
    except (ValueError, TypeError):
        return 0
def op_float(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx))
    except (ValueError, TypeError):
        return 0.0
def op_string(ctx, args):
    return str(checkifvar(args, 0, ctx))
def op_bool(ctx, args):
    val = checkifvar(args, 0, ctx)
    # Returns True for 1, "True", or non-empty strings
    if str(val).lower() in ["false", "0", "0.0", "none"]: return False
    return bool(val)
# --- CONTROL OPCODES (L-Blocks) ---
# These receive 'substack', which is a list of compiled lambdas.

def op_repeat(ctx, args, substack):
    times = int(float(checkifvar(args, 0, ctx)))
    for _ in range(times):
        for task in substack:
            task()

def op_if(ctx, args, substack):
    if checkifvar(args, 0, ctx):
        for task in substack:
            task()

def op_render(ctx, args):
    sprite_name = str(checkifvar(args, 0, ctx))
    
    target_surf = None
    for entry in ctx['assets']:
        if entry['name'] == sprite_name:
            target_surf = entry['surf']
            break
            
    if target_surf:
        x, y = float(checkifvar(args, 1, ctx)), float(checkifvar(args, 2, ctx))
        ctx['screen'].blit(target_surf, (x, y))

def op_fill(ctx, args):
    # Fill screen [r][g][b]
    # args: [255, 255, 255]
    color = (int(checkifvar(args, 0, ctx)), int(checkifvar(args, 1, ctx)), int(checkifvar(args, 2, ctx)))
    ctx['screen'].fill(color)

def set_var(ctx, args):
    var_name = str(args[0])
    value = checkifvar(args, 1, ctx) 
    ctx["vars"][var_name] = value

def change_var(ctx, args):
    #args = [var_name, value]
    ctx["vars"][str(args[0])] = int(ctx["vars"][str(args[0])]) + int(checkifvar(args, 1, ctx))

def op_wait(ctx, args):
    # Wait [seconds]
    # args: [1.0]
    pygame.time.wait(int(float(checkifvar(args, 0, ctx)) * 1000))

def op_stop_all(ctx, args):
    # Stop all sounds
    pygame.mixer.stop()

def show_console(ctx, args):
    ctx['console'].active = True

def hide_console(ctx, args):
    ctx['console'].active = False

def print_to_console(ctx, args):
    # args[0] is the text from the block
    ctx['console'].log(checkifvar(args, 0, ctx))

# --- MAPPING ---
OPCODES = {
    # Commands
    "Render": op_render,
    "Fill": op_fill,
    "Variable": set_var,   # Matching your "Variable [string] = []" template
    "Change": change_var,   # Matching your "Change [string] by [num]" template
    "Wait": op_wait,
    "Print": print_to_console,
    "Stop all": op_stop_all,
    "Show Console": show_console,
    "Hide Console": hide_console,
    
    # Reporters (O-Blocks)
    "+": op_add,
    "-": op_sub,
    "*": op_mul,
    "/": op_div,
    "int": op_int,
    "float": op_float,
    "string": op_string,
    "bool": op_bool,
    "Get": op_get, # To retrieve variable values
    
    # Control (L-Blocks)
    "Repeat": op_repeat,
    "If": op_if
}