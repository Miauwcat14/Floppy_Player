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
    # The condition is the first argument (index 0)
    condition = checkifvar(args, 0, ctx)
    
    # In Python, True is 1 and False is 0 in your engine usually
    if condition:
        # Run every task inside the if-mouth
        for task in substack:
            task()

def op_key_pressed(ctx, args):
    # 1. Resolve the key name (in case it's a variable)
    from block_code import checkifvar
    key_name = str(checkifvar(args, 0, ctx)).lower()
    
    # 2. Update Pygame's internal state
    pygame.event.pump() 
    
    try:
        # 3. Get the ID and check the state
        key_id = pygame.key.key_code(key_name)
        keys = pygame.key.get_pressed()
        
        # We return 1 for True, 0 for False (standard for your engine)
        return 1 if keys[key_id] else 0
    except ValueError:
        return 0

def op_rect_touching(ctx, args):
    # Rect touching [x1][y1][w1][h1] with [x2][y2][w2][h2]
    r1 = pygame.Rect(checkifvar(args,0,ctx), checkifvar(args,1,ctx), checkifvar(args,2,ctx), checkifvar(args,3,ctx))
    r2 = pygame.Rect(checkifvar(args,4,ctx), checkifvar(args,5,ctx), checkifvar(args,6,ctx), checkifvar(args,7,ctx))
    return r1.colliderect(r2)

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
    "Variable": set_var,   
    "Change": change_var,   
    "Wait": op_wait,
    "Stop all": op_stop_all,
    
    # System
    "Print": print_to_console,
    "Show Console": show_console,
    "Hide Console": hide_console,
    "delta": lambda ctx, args: ctx.get('dt', 0.016), 
    
    # Reporters (O-Blocks)
    "+": op_add,
    "-": op_sub,
    "*": op_mul,
    "/": op_div,
    "int": op_int,
    "float": op_float,
    "string": op_string,
    "bool": op_bool,
    "Get": op_get, 
    
    # Detection
    "key_pressed": op_key_pressed,
    "rect_touching": op_rect_touching,
    
    # Control (L-Blocks)
    "Repeat": op_repeat,
    "If": op_if
}