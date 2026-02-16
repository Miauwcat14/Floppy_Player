import pygame

def __Liv__(args, num, ctx): #Look if var
    if num >= len(args):return 0 
    st = str(args[num])
    if st.startswith("var:"):
        var_name = st[4:]
        if var_name in ctx["vars"]:return ctx["vars"][var_name]
    return args[num]

def __Gvt__(args, num, ctx): #Get var type
    if num >= len(args):return 0 
    st = str(args[num])
    if st.startswith("type:"):
        var_name = st[4:]
        if var_name in ctx["vars"]:return type(ctx["vars"][var_name])
    return args[num]

def checkifvar(args, num, ctx):
    st = str(args[num])
    if st.startswith("type:"):
        return __Gvt__(args, num, ctx)
    if st.startswith("var:"):
        return __Liv__(args, num, ctx)
    return args[num]

def op_render(ctx, args):
    # args = [sprite_name, x, y]
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
    #args = [var_name, var_value]
    ctx["vars"][str(args[0])] = args[1]

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
# Make sure the key matches the FIRST WORD of your template name!
OPCODES = {
    "Render": op_render,
    "Fill screen": op_fill,
    "Variable": set_var,
    "Change": change_var,
    "Show Console": show_console,
    "Hide Console": hide_console,
    "Print": print_to_console,
    "Wait": op_wait,
    "Stop all": op_stop_all,
    "Repeat": None # Handled automatically by the Compiler's loop logic!
}