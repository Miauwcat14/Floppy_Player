import pygame
import random
import math

def checkifvar(args, num, ctx):
    profiler = ctx.get("profiler")
    start = profiler.start_checkifvar() if profiler else None

    try:
        if num >= len(args):
            return 0

        val = args[num]

        if isinstance(val, dict) and val.get("type") == "expr":
            opcode_name = val.get("opcode").strip("() ")
            params = val.get("params", [])

            if opcode_name in OPCODES:
                return OPCODES[opcode_name](ctx, params)
            return 0

        st = str(val)

        if st.startswith("var:"):
            var_name = st[4:]
            return ctx["vars"].get(var_name, 0)

        if st.startswith("type:"):
            var_name = st[5:]
            return type(ctx["vars"].get(var_name, 0))

        try:
            if "." in st:
                return float(st)
            return int(st)
        except:
            return val

    finally:
        if profiler:
            profiler.end_checkifvar(start)

def math_dispatcher(ctx, args):
    return float(checkifvar(args, 0, ctx)) + float(checkifvar(args, 1, ctx))

def op_add(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) + float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return 0
def op_sub(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) - float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return 0
def op_mul(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) * float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return 0
def op_div(ctx, args):
    try:
        d = float(checkifvar(args, 1, ctx))
        return float(checkifvar(args, 0, ctx)) / d if d != 0 else 0
    except (ValueError, TypeError):
        return 0

def op_eq(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) == float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return False
def op_gt(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) > float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return False
def op_lt(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) < float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return False
def op_gte(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) >= float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return False
def op_lte(ctx, args):
    try:
        return float(checkifvar(args, 0, ctx)) <= float(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return False

def op_not(ctx, args):
    try:
        return not bool(checkifvar(args, 0, ctx))
    except (ValueError, TypeError):
        return False
def op_and(ctx, args):
    try:
        return bool(checkifvar(args, 0, ctx)) and bool(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return False
def op_or(ctx, args):
    try:
        return bool(checkifvar(args, 0, ctx)) or bool(checkifvar(args, 1, ctx))
    except (ValueError, TypeError):
        return False

def op_get(ctx, args):
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
    if str(val).lower() in ["false", "0", "0.0", "none"]: return False
    return bool(val)


def op_repeat(ctx, args, substack):
    times = int(float(checkifvar(args, 0, ctx)))
    for _ in range(times):
        for task in substack:
            task()

def op_if(ctx, args, substack):
    # checkifvar will resolve the Get blocks or Comparisons
    condition = checkifvar(args, 0, ctx)
    
    # We force it to a boolean. 
    # In your engine: 0, "0", "False", or empty strings become False.
    if bool(condition) and str(condition).lower() not in ["false", "0", "0.0"]:
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
    # Get values and force them to be 0-255
    r = int(checkifvar(args, 0, ctx))
    g = int(checkifvar(args, 1, ctx))
    b = int(checkifvar(args, 2, ctx))
    
    # CLAMPING: If r is 600, it becomes 255. If r is -50, it becomes 0.
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    
    ctx['rgb'] = (r, g, b)

def set_var(ctx, args):
    var_name = str(args[0])
    value = checkifvar(args, 1, ctx) 
    ctx["vars"][var_name] = value

def change_var(ctx, args):
    #args = [var_name, value]
    ctx["vars"][str(args[0])] = int(ctx["vars"][str(args[0])]) + int(checkifvar(args, 1, ctx))

def op_wait(ctx, args):
    seconds = float(checkifvar(args, 0, ctx))
    # We set a timestamp in the future
    ctx['sleep_until'] = pygame.time.get_ticks() + int(seconds * 1000)

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

def op_clear_console(ctx, args):
    ctx['console'].logs = [] # Wipe the list

#Lists
def op_create_list(ctx, args):
    list_name = str(args[0])
    ctx["vars"][list_name] = [] # Create a real Python list in memory

def op_add_to_list(ctx, args):
    # args[0] is the value, args[1] is the list name
    val = checkifvar(args, 0, ctx)
    list_name = str(args[1])
    
    # Safety: Create list if the user forgot the 'Create List' block
    if list_name not in ctx["vars"]:
        ctx["vars"][list_name] = []
        
    if isinstance(ctx["vars"][list_name], list):
        ctx["vars"][list_name].append(val)

def op_list_length(ctx, args):
    list_name = str(args[0])
    lst = ctx["vars"].get(list_name, [])
    return len(lst) if isinstance(lst, list) else 0

def op_get_item(ctx, args):
    list_name = str(checkifvar(args, 0, ctx))
    index = int(checkifvar(args, 1, ctx))
    lst = ctx["vars"].get(list_name, [])
    if 0 <= index < len(lst):
        return lst[index]
    return 0

def op_mod(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    b = float(checkifvar(args, 1, ctx))
    return a % b

def op_round(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    return round(a)

def op_sqrt(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    return math.sqrt(a)

def op_power(ctx, args):
    base = checkifvar(args, 0, ctx)
    exponent = checkifvar(args, 1, ctx)
    return base ** exponent 

def op_sin(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    return math.sin(a)

def op_cos(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    return math.cos(a)

def op_tan(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    return math.tan(a)

def op_atan(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    return math.atan(a)

def op_abs(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    return abs(a)

def op_random(ctx, args):
    a = float(checkifvar(args, 0, ctx))
    b = float(checkifvar(args, 1, ctx))
    return random.randint(a, b)

# --- MAPPING ---
OPCODES = {
    # Commands
    "Render": op_render,
    "Fill screen": op_fill,
    "Variable": set_var,   
    "Change": change_var,   
    "Wait": op_wait,
    "Stop all": op_stop_all,
    
    # System
    "Print": print_to_console,
    "Show Console": show_console,
    "Hide Console": hide_console,
    "Clear Console": op_clear_console,
    "delta": lambda ctx, args: ctx.get('dt', 0.016),
    "time": lambda ctx, args: pygame.time.get_ticks() / 1000.0,
    "True": lambda ctx, args: True,
    "False": lambda ctx, args: False,
    "None": lambda ctx, args: None,
    "mouse x": lambda ctx, args: ctx.get('mouse').hitbox.x if ctx.get('mouse') else 0,
    "mouse y": lambda ctx, args: ctx.get('mouse').hitbox.y if ctx.get('mouse') else 0,
    "screen x": lambda ctx, args: ctx.get('screen', 0).get_width(),
    "screen y": lambda ctx, args: ctx.get('screen', 0).get_height(),
    
    # Reporters (O-Blocks)
    "+": op_add,
    "-": op_sub,
    "*": op_mul,
    "/": op_div,
    "%": op_mod,
    "=": op_eq,
    ">": op_gt,
    "<": op_lt,
    ">=": op_gte,
    "<=": op_lte,
    "int": op_int,
    "float": op_float,
    "string": op_string,
    "bool": op_bool,
    "Get": op_get,
    "not": op_not,
    "and": op_and,
    "or": op_or,
    "round": op_round,
    "abs": op_abs,
    "sqrt": op_sqrt,
    "power": op_power,
    "sin": op_sin,
    "cos": op_cos,
    "tan": op_tan,
    "atan": op_atan,
    "random": op_random,
    
    # Detection
    "key_pressed": op_key_pressed,
    "rect_touching": op_rect_touching,
    
    # Control (L-Blocks)
    "Create List": op_create_list,
    "Add": op_add_to_list,         # Changed from "Add to"
    "Item": op_get_item,
    "Length of": op_list_length,   # Changed from "Length"
    "For Each": None,
    "Repeat": op_repeat,
    "If": op_if,
    "While": None,
    "Forever while": None,
}

SCHEDULER_DEPENDENT = {
    "Wait",
    "Render",
    "Fill screen",
    "key pressed",
    "Forever while",
}