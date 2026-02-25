import pygame
import sys
import math
import os
from button import *
from font import *
from mouse import *  
from reader import *
from block import *
from fexplorer import *
from assets_st import *
from OPcompiler import *
from save_load import *

def main():
    pygame.init()
    # Display
    screen_size = pygame.display.Info()
    side = min(screen_size.current_w, screen_size.current_h)
    window_size = (screen_size.current_w, side)
    screen = pygame.Surface((455, 256))
    window_limits = (455, 256)
    display = pygame.display.set_mode((screen_size.current_w, screen_size.current_h) ,pygame.DOUBLEBUF | pygame.FULLSCREEN)

    # Program variables
    clock = pygame.time.Clock()
    FPS_CAP = 60
    dt = 0
    run = True 
    is_menu = True
    is_error = False
    is_explorer = False
    is_storage = False

    # Variables init
    sensitivity = 0.25
    mouse = Mouse()

    def close_browser():
        nonlocal is_storage
        is_storage = False

    def open_file_dialog():
        nonlocal is_explorer
        is_explorer = True

    storage = AssetsStorage(
        pygame.Rect(0, 0, 256, 256),
        mouse=mouse,
        on_close=close_browser, 
        on_load_request=open_file_dialog
    )
    explorer = FileExplorer()
    home_b = Button((1, 1, 23, 23))
    assets_b = Button((60, 1, 24, 24))
    play_b = Button((90, 1, 24, 24))
    font = Font("Fonts/power clear.ttf", 12)
    home = pygame.image.load("assets/home.png").convert()
    home_h = pygame.image.load("assets/home_h.png").convert()
    ed_bg = pygame.image.load("assets/editor_bg.png").convert_alpha()
    trash = pygame.image.load("assets/trash.png").convert_alpha()
    trash_h = pygame.image.load("assets/trash_h.png").convert_alpha()
    trash_rect = pygame.Rect(228, 2, 24, 24)
    assets = pygame.image.load("assets/files.png").convert_alpha()
    assets_h = pygame.image.load("assets/files_h.png").convert_alpha()
    play = pygame.image.load("assets/start.png").convert_alpha()
    play_h = pygame.image.load("assets/start_h.png").convert_alpha()
    
    toolbox_templates = [
        {"name": "Render [string:sprite name] at [num:0][num:0]", "col": (100, 100, 255), "desc": "Render a sprite from you´re assets into the screen at a coordinate: x, y."},
        {"name": "Fill screen [number:255][number:255][number:255] rgb", "col": (100, 100, 255), "desc": "Fill the screen with a rgb value color."},
        {"name": "[number:0]+[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Add 2 numbers together."},
        {"name": "[number:0]-[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "subtract 2 numbers."},
        {"name": "[number:0]*[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Multiply 2 numbers together."},
        {"name": "[number:0]/[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Divide 2 numbers."},
        {"name": "[number:0]%[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the remainder of a division."},
        {"name": "abs[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the absolute value of a number."},
        {"name": "round[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Rounds a number to the nearest integer."},
        {"name": "sin[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the sine of a number."},
        {"name": "cos[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the cosine of a number."},
        {"name": "tan[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the tangent of a number."},
        {"name": "atan[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the arc tangent of a number."},
        {"name": "sqrt[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the square root of a number."},
        {"name": "random[number:0] to [number:10]", "col": (152, 209, 140), "btype": "o", "desc": "Returns a random number between the two numbers."},
        {"name": "[number:0]power[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the first number raised to the power of the second number."},
        {"name": "[number:0]=[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Check if 2 numbers are equal."},
        {"name": "[number:0]>[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Check if the first number is greater than the second."},
        {"name": "[number:0]<[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Check if the first number is less than the second."},
        {"name": "[number:0]>=[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Check if the first number is greater than or equal to the second."},
        {"name": "[number:0]<=[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Check if the first number is less than or equal to the second."},
        {"name": "[number:0]and[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns True if both numbers are True."},
        {"name": "[number:0]or[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns True if at least one of the numbers is True."},
        {"name": "not[number:0]", "col": (152, 209, 140), "btype": "o", "desc": "Returns the opposite of a boolean value."},
        {"name": "int[number:0.0]", "col": (135, 206, 235), "btype": "o", "desc": "Convert a float to a integer."},
        {"name": "float[number:0]", "col": (135, 206, 235), "btype": "o", "desc": "Convert a integer to a float."},
        {"name": "string[]", "col": (135, 206, 235), "btype": "o", "desc": "Convert a variable into a string."},
        {"name": "bool[]", "col": (135, 206, 235), "btype": "o", "desc": "Convert a variable into a boolean."},
        {"name": "If [bool:0]", "col": (255, 171, 25), "btype": "l", "desc": "Execute the contained blocks only if the condition is true."},
        {"name": "Repeat [number:10]", "col": (255, 171, 25), "btype": "l", "desc": "Repeat the contained blocks 10 times. Useful for simple loops."},
        {"name": "While [number:1]", "col": (255, 171, 25), "btype": "l", "desc": "Repeats the contained blocks while the condition is true."},
        {"name": "Forever while [number:1]", "col": (255, 171, 25), "btype": "l", "desc": "Repeats the contained blocks while the condition is true fps dependent so no screen freezers hit."},
        {"name": "key_pressed[string:space]", "col": (135, 206, 235), "btype": "o", "desc": "Returns True if the specified key is currently pressed."},
        {"name": "delta", "col": (135, 206, 235), "btype": "o", "desc": "Returns the time in seconds since the last frame (delta time)."},
        {"name": "time", "col": (135, 206, 235), "btype": "o", "desc": "Returns the time in seconds since the game started."},
        {"name": "True", "col": (135, 206, 235), "btype": "o", "desc": "Returns True."},
        {"name": "False", "col": (135, 206, 235), "btype": "o", "desc": "Returns False."},
        {"name": "None", "col": (135, 206, 235), "btype": "o", "desc": "Returns None."},
        {"name": "mouse x", "col": (135, 206, 235), "btype": "o", "desc": "Returns the x position of the mouse."},
        {"name": "mouse y", "col": (135, 206, 235), "btype": "o", "desc": "Returns the y position of the mouse."},
        {"name": "screen x", "col": (135, 206, 235), "btype": "o", "desc": "Returns the x position of the screen."},
        {"name": "screen y", "col": (135, 206, 235), "btype": "o", "desc": "Returns the y position of the screen."},
        {"name": "Variable [string:variable] = []", "col": (255, 128, 0), "desc": "Sets a value to a given variable or creates a new one entirelly."},
        {"name": "Change [string:variable] by [num:1]", "col": (255, 128, 0), "desc": "Changes the value of a float or integer type: variable by a input number."},
        {"name": "Get [string:variable]", "col": (255, 128, 0), "btype": "o", "desc": "Returns the value of a variable."},
        {"name": "Create List [string:bullets]", "col": (150, 0, 255), "desc": "Initializes a new empty list with the given name."},
        {"name": "Add [num:0] to [string:bullets]", "col": (150, 0, 255), "desc": "Appends a value to the end of a specified list."},
        {"name": "Item [num:0] of [string:bullets]", "col": (150, 0, 255), "btype": "o", "desc": "Returns the value at a specific index in a list."},
        {"name": "Length of [string:bullets]", "col": (150, 0, 255), "btype": "o", "desc": "Returns how many items are currently in the list."},
        {"name": "For Each [string:i] in [string:bullets]", "col": (150, 0, 255), "btype": "l", "desc": "Loops through every item in a list, setting the first variable to the current item."},
        {"name": "Wait [number:1] sec", "col": (200, 100, 0), "desc": "Pause execution for one second. Timing is approximate and frame-rate dependent."},
        {"name": "Set volume [number:100]", "col": (0, 150, 150), "desc": "Set the master volume level for sound playback (0 - 100)."},
        {"name": "Play note [string:C4]", "col": (150, 0, 150), "desc": "Play a musical note for a short duration. Specify pitch and length in the block parameters."},
        {"name": "Stop all", "col": (80, 80, 80), "desc": "Stop all currently playing sounds and reset audio state."},
        {"name": "Show Console", "col": (204, 0, 0), "desc": "Display the debug console overlay."},
        {"name": "Hide Console", "col": (204, 0, 0), "desc": "Hide the debug console overlay."},
        {"name": "Clear Console", "col": (204, 0, 0), "desc": "Clear all messages from the console."},
        {"name": "Print [string:Hello!]", "col": (204, 0, 0), "desc": "Print a message to the in-game console."},
    ]

    toolbox_blocks = []
    tb_base_x = 3
    last = 23
    tb_spacing = 6
    for spec in toolbox_templates:
        b = Block(spec["name"], spec["col"], (tb_base_x, 0), btype=spec.get("btype", "n"))
        b.pos[1] = last
        last = last + b.get_toolbox_height() + tb_spacing
        b.desc = spec.get("desc", spec["name"])
        toolbox_blocks.append(b)

    hover_timers = [None] * len(toolbox_blocks)
    HOVER_TOOLTIP_DELAY_MS = 1500

    # THE MASTER VARIABLES
    blocks = []
    target_block = None # Completely replaces active_block
    input_block = None   
    input_block_idx = None

    def b_hover(bt, norm, hover):
        if bt.hover:
            bt.render(screen, norm)
            mouse.set_state(1)
        else:
            bt.render(screen, hover)

    tb_view = pygame.Rect(0, 32, 96, 224)
    scroll_offset = -10
    scrollbar_dragging = False
    scrollbar_handle_rect = pygame.Rect(0,0,0,0)
    scrollbar_drag_y = 0

    def compute_toolbox_content_height():
        if not toolbox_blocks: return 0
        total = 0
        for tb in toolbox_blocks:
            total += tb.get_toolbox_height() + tb_spacing
        return total

    def clamp(v, a, b):
        return max(a, min(b, v))

    def wrap_text(text, max_width):
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip() if cur else w
            tw, th = font.font.size(test)
            if tw <= max_width:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return lines
    
    def delete_chain(block_to_remove, blocks_list):
        if block_to_remove.child:
            delete_chain(block_to_remove.child, blocks_list)
        if block_to_remove.nested_child:
            delete_chain(block_to_remove.nested_child, blocks_list)
        if block_to_remove in blocks_list:
            blocks_list.remove(block_to_remove)

    def distance_to_rect(point, rect):
        closest_x = max(rect.left, min(point[0], rect.right))
        closest_y = max(rect.top, min(point[1], rect.bottom))
        dx = point[0] - closest_x
        dy = point[1] - closest_y
        return math.sqrt(dx*dx + dy*dy)

    engine = FloppyCompiler(screen, storage.entries)

    class Console:
        def __init__(self, font_instance):
            self.font = font_instance
            self.messages = []
            self.active = False
            self.rect = pygame.Rect(0, 160, 456, 96)

        def log(self, text, color=(255, 255, 255)):
            self.messages.append((str(text), color))
            if len(self.messages) > 7: self.messages.pop(0)
            print(f"[Console] {text}") 

        def draw(self, surface):
            if not self.active: return
            overlay = pygame.Surface((self.rect.width, self.rect.height))
            overlay.set_alpha(180)
            overlay.fill((10, 10, 25))
            surface.blit(overlay, (self.rect.x, self.rect.y))
            pygame.draw.line(surface, (100, 100, 255), (0, self.rect.y), (256, self.rect.y), 1)
            for i, (msg, col) in enumerate(self.messages):
                self.font.render(surface, msg, col, 12, (5, self.rect.y + 5 + (i * 12)))

    console = Console(font)
    engine.ctx['console'] = console
    engine.ctx['mouse'] = mouse

    #####################
    # -=Main Loop=-     #
    #####################

    while run:
        last_time = pygame.time.get_ticks()
        events = pygame.event.get()
        ox = (screen_size.current_w - window_size[0]) // 2
        mouse_pos = pygame.mouse.get_pos()
        lim_x, lim_y = window_limits
        if mouse_pos[0] > (lim_x - 1) / sensitivity:
            pygame.mouse.set_pos(((lim_x - 1) / sensitivity, mouse_pos[1]))
        if mouse_pos[1] > (lim_y - 1) / sensitivity:
            pygame.mouse.set_pos((mouse_pos[0], (lim_y - 1) / sensitivity))
        mpos = mouse.hitbox.center

        for event in events:
            if event.type == pygame.QUIT:
                run = False

        if engine.ctx["running"]:
            screen.fill(engine.ctx["rgb"])
            mouse.set_state(0)
            
            # Run the engine (this now respects the non-blocking wait)
            engine.run_once()
            
            # Always draw the console if it's active
            console.draw(screen) 
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    engine.ctx['running'] = False
                    engine.ctx['finished'] = False
                    engine.ctx['pc'] = 0           # <--- IMPORTANT: RESET TO START
                    engine.ctx['sleep_until'] = 0  # <--- IMPORTANT: RESET TIMER
                    engine.ctx['console'].messages = [] # Use .messages to clear
                    print("Engine Stopped. Returning to Editor...")
        else:
            screen.fill((255, 255, 255))
            screen.blit(ed_bg, (0, 0))
            if is_explorer:
                status = explorer.update(events, mouse)
                explorer.draw(screen, mouse)
                
                if status == "cancel":
                    is_explorer = False
                elif status == "ok":
                    if explorer.selected_file:
                        try:
                            storage.add_image(explorer.selected_file, "new")
                        except Exception:
                            pass
                    is_explorer = False
                
                mouse.render(screen, sensitivity)
                sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
                display.blit(sc, (ox, 0))
                pygame.display.flip()
                clock.tick(FPS_CAP)
                continue
            
            for event in events:
                if event.type == pygame.QUIT:
                    run = False
                
                if is_storage:
                    storage.handle_event(event)
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        is_storage = False
                    continue

                if event.type == pygame.KEYDOWN:
                    if input_block is not None:
                        consumed = input_block.handle_key(event)
                        if consumed:
                            if input_block.editing_index is None:
                                input_block = None
                                input_block_idx = None
                            continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        scroll_offset = clamp(scroll_offset - 16, -10, max(0, compute_toolbox_content_height() - tb_view.h))
                    elif event.button == 5:
                        scroll_offset = clamp(scroll_offset + 16, -10, max(0, compute_toolbox_content_height() - tb_view.h))

                if event.type == pygame.MOUSEWHEEL:
                    scroll_offset = clamp(scroll_offset - event.y * 20, -10, max(0, compute_toolbox_content_height() - tb_view.h))

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if input_block is not None:
                        idx_hit = input_block.input_at(mpos)
                        if idx_hit != input_block_idx:
                            input_block.stop_edit_input(commit=True)
                            input_block = None
                            input_block_idx = None
                        if input_block is not None:
                            continue

                    if scrollbar_handle_rect.collidepoint(mpos):
                        scrollbar_dragging = True
                        scrollbar_drag_y = mpos[1] - scrollbar_handle_rect.y
                        continue

                    spawned = False
                    if tb_view.collidepoint(mpos):
                        for idx, tb in enumerate(toolbox_blocks):
                            tb_w, tb_h = tb.get_size()
                            tb_rect = pygame.Rect(tb.pos[0], tb.pos[1] - scroll_offset, tb_w, tb_h)
                            if tb_rect.collidepoint(mpos):
                                new_block = Block(tb.text, tb.color, (tb_rect.x, tb_rect.y), btype=tb.btype) 
                                new_block.dragging = True
                                new_block.offset = [new_block.pos[0] - mpos[0], new_block.pos[1] - mpos[1]]
                                blocks.append(new_block)
                                target_block = new_block
                                spawned = True
                                hover_timers[idx] = None
                                break

                    if not spawned:
                        for b in reversed(blocks):
                            found = b.get_block_at(mpos)
                            if found:
                                # 1. CHECK FOR O-BLOCKS IN SLOTS FIRST
                                slot_hit = found.input_at(mpos)
                                if slot_hit is not None:
                                    val = found.slots[slot_hit]["value"]
                                    
                                    # If the value in the slot is actually another Block (O-block)
                                    if isinstance(val, Block):
                                        target_block = val
                                        # Reset the slot to its default text so it's not empty
                                        found.slots[slot_hit]["value"] = found.slots[slot_hit].get("default", "")
                                        
                                        target_block.parent = None
                                        if target_block not in blocks:
                                            blocks.append(target_block)
                                        
                                        target_block.dragging = True
                                        target_block.offset = [target_block.pos[0] - mpos[0], target_block.pos[1] - mpos[1]]
                                        
                                        # Move to front
                                        blocks.remove(target_block)
                                        blocks.append(target_block)
                                        break 

                                    # 2. IF SLOT IS TEXT, START EDITING
                                    else:
                                        found.start_edit_input(slot_hit)
                                        input_block = found
                                        input_block_idx = slot_hit
                                        break
                                
                                # 3. STANDARD UNPLUG (for stacked blocks)
                                else:
                                    if found.parent:
                                        p = found.parent
                                        # Clear references from parent
                                        if p.child == found: p.child = None
                                        if p.nested_child == found: p.nested_child = None
                                        
                                        # Handle O-block unplug if it wasn't caught by slot_hit 
                                        # (Safety for different collision shapes)
                                        for s in p.slots:
                                            if s["value"] == found:
                                                s["value"] = s.get("default", "")

                                        found.parent = None
                                        if found not in blocks:
                                            blocks.append(found)

                                    target_block = found
                                    target_block.dragging = True
                                    target_block.offset = [target_block.pos[0] - mpos[0], target_block.pos[1] - mpos[1]]
                                    
                                    blocks.remove(target_block)
                                    blocks.append(target_block)
                                    break

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if target_block:
                        target_block.dragging = False
                        
                        if target_block.get_rect().colliderect(trash_rect):
                            delete_chain(target_block, blocks)
                        else:
                            # Try to snap
                            snapped = target_block.try_snap(blocks)
                            
                            if snapped:
                                # If it snapped, it should be removed from the top-level list
                                if target_block in blocks:
                                    blocks.remove(target_block)
                            else:
                                # SAFETY: If it's NOT snapped and NOT in the list, put it back!
                                if target_block not in blocks and target_block.parent is None:
                                    blocks.append(target_block)
                        
                        target_block = None

                    scrollbar_dragging = False

                if event.type == pygame.MOUSEMOTION:
                    if scrollbar_dragging:
                        handle_area_h = tb_view.h
                        content_h = compute_toolbox_content_height()
                        max_scroll = max(0, content_h - tb_view.h)
                        rel_y = clamp(mpos[1] - scrollbar_drag_y - tb_view.y, 0, max(0, handle_area_h - scrollbar_handle_rect.h))
                        if max_scroll > 0 and handle_area_h - scrollbar_handle_rect.h > 0:
                            scroll_offset = int((rel_y / (handle_area_h - scrollbar_handle_rect.h)) * max_scroll)
                        else:
                            scroll_offset = 0
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        if not os.path.exists("saves"):
                            os.makedirs("saves")
                        save_project(all_blocks, "saves/my_script.floppy")
                        
                    if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        # Clear current workspace
                        all_blocks.clear()
                        # Load new blocks
                        loaded = load_project("saves/my_script.floppy", self)
                        all_blocks.extend(loaded)

            mouse.set_state(0)
            
            # TRASH CAN HOVER LOGIC
            if target_block:
                if target_block.get_rect().colliderect(trash_rect):
                    dist = distance_to_rect(mpos, trash_rect)
                    if dist < 31:
                        screen.blit(trash_h, (trash_rect.x, trash_rect.y))
                        mouse.set_state(1)
                    else:
                        screen.blit(trash, (trash_rect.x, trash_rect.y))
                else:
                    screen.blit(trash, (trash_rect.x, trash_rect.y))
            else:
                screen.blit(trash, (trash_rect.x, trash_rect.y))

            for b in blocks: #b.stamp(s)
                b.update(mpos, blocks)

            if is_storage:
                storage.render(screen)
            elif is_menu:
                if not is_error:
                    if home_b.update(mouse): run = False
                    if assets_b.update(mouse): is_storage = True
                    
                    if play_b.update(mouse):
                        root = None
                        for b in blocks:
                            if b.parent is None: 
                                root = b
                                break
                                
                        if root:
                            engine.compile(root)
                            console.messages = []
                            engine.ctx['running'] = True
                            print("Game Started!")

                    if not is_explorer:
                        b_hover(assets_b, assets_h, assets)
                        b_hover(home_b, home_h, home)
                        b_hover(play_b, play_h, play)

                        pygame.draw.rect(screen, (12, 46, 86), tb_view, border_radius=2)
                        inner = tb_view.inflate(-4, -4)
                        pygame.draw.rect(screen, (22, 66, 106), inner, border_radius=2)

                        content_h = compute_toolbox_content_height()
                        max_scroll = max(0, content_h - tb_view.h)
                        if content_h > 0:
                            handle_h = int(max(12, tb_view.h * (tb_view.h / content_h)))
                        else:
                            handle_h = tb_view.h
                        handle_h = clamp(handle_h, 12, tb_view.h)
                        if max_scroll > 0:
                            handle_rel = scroll_offset / max_scroll
                        else:
                            handle_rel = 0.0
                        handle_y = tb_view.y + int(handle_rel * (tb_view.h - handle_h))
                        scrollbar_x = tb_view.right + 2
                        scrollbar_width = 8
                        scrollbar_rect = pygame.Rect(scrollbar_x, tb_view.y, scrollbar_width, tb_view.h)
                        scrollbar_handle_rect = pygame.Rect(scrollbar_x, handle_y, scrollbar_width, handle_h)

                        pygame.draw.rect(screen, (30, 30, 30), scrollbar_rect, border_radius=4)
                        pygame.draw.rect(screen, (180, 180, 180), scrollbar_handle_rect, border_radius=4)

                        prev_clip = screen.get_clip()
                        screen.set_clip(tb_view)

                        current_ticks = pygame.time.get_ticks()
                        for idx, tb in enumerate(toolbox_blocks):
                            tb_w, tb_h = tb.get_size()
                            render_x = tb.pos[0]
                            render_y = tb.pos[1] - scroll_offset
                            tb_rect = pygame.Rect(render_x, render_y, tb_w, tb_h)
                            hovered = tb_rect.collidepoint(mpos)
                            tb.hovered = hovered

                            if hovered:
                                if hover_timers[idx] is None:
                                    hover_timers[idx] = current_ticks
                            else:
                                hover_timers[idx] = None

                            tb.stamp_at(screen, (render_x, render_y))
                        screen.set_clip(prev_clip)

                        for b in blocks:
                            is_owned_as_child = any(other.child == b for other in blocks)
                            is_owned_as_nested = any(other.nested_child == b for other in blocks)
                            
                            if not is_owned_as_child and not is_owned_as_nested:
                                b.stamp(screen)
                else:
                    font.render(screen, "ERROR 404", (255, 0, 0), 24, (30, 188))

                if not is_explorer:
                    tooltip_to_show = None
                    now = pygame.time.get_ticks()
                    for idx, start in enumerate(hover_timers):
                        if start is not None and now - start >= HOVER_TOOLTIP_DELAY_MS:
                            tooltip_to_show = toolbox_blocks[idx].desc if hasattr(toolbox_blocks[idx], "desc") else toolbox_blocks[idx].text
                            break

                    if tooltip_to_show is not None:
                        MAX_TIP_W = 140
                        pad_x, pad_y = 6, 6
                        lines = wrap_text(tooltip_to_show, MAX_TIP_W - pad_x * 2)
                        tw, th = 0, 0
                        line_heights = []
                        for ln in lines:
                            s_w, s_h = font.font.size(ln)
                            tw = max(tw, s_w)
                            line_heights.append(s_h)
                            th += s_h
                        box_w = tw + pad_x * 2
                        box_h = th + pad_y * 2
                        tip_x = int(mpos[0] + 10)
                        tip_y = int(mpos[1] + 12)
                        tip_x = clamp(tip_x, 0, 256 - box_w - 2)
                        tip_y = clamp(tip_y, 0, 256 - box_h - 2)

                        tooltip_rect = pygame.Rect(tip_x, tip_y, box_w, box_h)
                        pygame.draw.rect(screen, (255, 255, 225), tooltip_rect, border_radius=4)
                        pygame.draw.rect(screen, (120, 120, 120), tooltip_rect, width=1, border_radius=4)

                        cur_y = tip_y + pad_y
                        for i, ln in enumerate(lines):
                            font.render(screen, ln, (0,0,0), 12, (tip_x + pad_x, cur_y))
                            cur_y += line_heights[i]

                if is_storage:
                    storage.render(screen)
                if is_explorer:
                    explorer.update(events, mouse)
                    explorer.draw(screen, mouse)

        mouse.render(screen, sensitivity)
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, (ox, 0))
        pygame.display.flip()
        current_time = pygame.time.get_ticks()
        dt = (current_time - last_time) / 1000.0 
        last_time = current_time
        engine.ctx["dt"] = dt
        clock.tick(FPS_CAP)
        pygame.display.set_caption(f"Floppy Player - FPS: {int(clock.get_fps())}")

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()