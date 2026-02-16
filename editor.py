import pygame
import sys
import math
from button import *
from font import *
from mouse import *
from reader import *
from block import *
from fexplorer import *
from assets_st import *
from OPcompiler import *

def main():
    pygame.init()
    # Display
    screen_size = pygame.display.Info()
    side = min(screen_size.current_w, screen_size.current_h)
    window_size = (side, side)
    screen = pygame.Surface((256, 256))
    display = pygame.display.set_mode((screen_size.current_w, screen_size.current_h) ,pygame.DOUBLEBUF | pygame.FULLSCREEN)

    # Program variables
    clock = pygame.time.Clock()
    FPS_CAP = 60
    run = True
    is_menu = True
    is_error = False
    is_explorer = False
    is_storage = False

    # Variables init
    sensitivity = 0.25

    # Assets init
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
    
    # Define the blocks that will live in the sidebar
    # slot syntax supports [type:value] where type is "number" or "string",
    # or simply [value] and type will be autodetected.
    toolbox_templates = [
        {"name": "Render [string:sprite name] at [num:0][num:0]", "col": (100, 100, 255), "desc": "Render a sprite from you´re assets into the screen at a coordinate: x, y."},
        {"name": "Fill screen [number:255][number:255][number:255] rgb", "col": (100, 100, 255), "desc": "Fill the screen with a rgb value color."},
        {"name": "Repeat [number:10]", "col": (0,255,0), "btype": "l", "desc": "Repeat the contained blocks 10 times. Useful for simple loops."},
        {"name": "Variable [string:variable] = []", "col": (255, 128, 0), "desc": "Sets a value to a given variable or creates a new one entirelly."},
        {"name": "Change [string:variable] by [num:1]", "col": (255, 128, 0), "desc": "Changes the value of a float or integer type: variable by a input number."},
        {"name": "Wait [number:1] sec", "col": (200, 100, 0), "desc": "Pause execution for one second. Timing is approximate and frame-rate dependent."},
        {"name": "Set volume [number:100]", "col": (0, 150, 150), "desc": "Set the master volume level for sound playback (0 - 100)."},
        {"name": "Play note [string:C4]", "col": (150, 0, 150), "desc": "Play a musical note for a short duration. Specify pitch and length in the block parameters."},
        {"name": "Stop all", "col": (80, 80, 80), "btype": "o", "desc": "Stop all currently playing sounds and reset audio state."},
        {"name": "Show Console", "col": (204, 0, 0), "desc": "Display the debug console overlay."},
        {"name": "Hide Console", "col": (204, 0, 0), "desc": "Hide the debug console overlay."},
        {"name": "Print [string:Hello!]", "col": (204, 0, 0), "desc": "Print a message to the in-game console."}
    ]

    # Create the actual Block objects for the sidebar (base positions are in toolbox coords)
    toolbox_blocks = []
    tb_base_x = 3
    last = 23
    tb_spacing = 6
    for spec in toolbox_templates:
        b = Block(spec["name"], spec["col"], (tb_base_x, 0), btype=spec.get("btype", "n"))
        b.pos[1] = last
        last = last + b.get_rect().height + tb_spacing
        b.desc = spec.get("desc", spec["name"])
        toolbox_blocks.append(b)

    # Hover timers for tooltips
    hover_timers = [None] * len(toolbox_blocks)
    HOVER_TOOLTIP_DELAY_MS = 1500  # ms

    # This list holds the blocks actually being used in the workspace
    blocks = []
    active_block = None

    # Input editing state (which block & which slot is currently being edited)
    input_block = None   # Block instance being edited (workspace only)
    input_block_idx = None

    def b_hover(bt, norm, hover):
        if bt.hover:
            bt.render(screen, norm)
            mouse.set_state(1)
        else:
            bt.render(screen, hover)

    # Toolbox viewport and scrollbar state
    tb_view = pygame.Rect(0, 32, 96, 224)
    scroll_offset = -10
    scrollbar_dragging = False
    scrollbar_handle_rect = pygame.Rect(0,0,0,0)
    scrollbar_drag_y = 0

    def compute_toolbox_content_height():
        if not toolbox_blocks:
            return 0
        total = 0
        for tb in toolbox_blocks:
            total += tb.get_size()[1] + tb_spacing
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
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines
    
    def delete_chain(block_to_remove, blocks_list):
        # 1. Delete the Attached Child (Below)
        if block_to_remove.child:
            delete_chain(block_to_remove.child, blocks_list)
        
        # 2. Delete the Nested Child (Inside) - CRITICAL FIX
        if block_to_remove.nested_child:
            delete_chain(block_to_remove.nested_child, blocks_list)
            
        # 3. Remove self
        if block_to_remove in blocks_list:
            blocks_list.remove(block_to_remove)
    
    def distance_to_rect(point, rect):
        # Find the closest x and y coordinates on the rect to the point
        closest_x = max(rect.left, min(point[0], rect.right))
        closest_y = max(rect.top, min(point[1], rect.bottom))
        
        # Calculate distance between the point and this closest spot
        dx = point[0] - closest_x
        dy = point[1] - closest_y
        return math.sqrt(dx*dx + dy*dy)

    ################
    #DA ENGINEEE
    ################
    engine = FloppyCompiler(screen, storage.entries)

    class Console:
        def __init__(self, font_instance):
            self.font = font_instance  # This should be your custom Font object
            self.messages = []
            self.active = False
            self.rect = pygame.Rect(0, 160, 256, 96) # Positioned at the bottom

        def log(self, text, color=(255, 255, 255)):
            self.messages.append((str(text), color))
            if len(self.messages) > 7: # Prevents overflow
                self.messages.pop(0)
            print(f"[Console] {text}") 

        def draw(self, surface):
            if not self.active: return
            
            # Draw background overlay
            overlay = pygame.Surface((self.rect.width, self.rect.height))
            overlay.set_alpha(180)
            overlay.fill((10, 10, 25))
            surface.blit(overlay, (self.rect.x, self.rect.y))
            
            # Draw a small border/header
            pygame.draw.line(surface, (100, 100, 255), (0, self.rect.y), (256, self.rect.y), 1)
            
            # Render lines using your custom Font class
            for i, (msg, col) in enumerate(self.messages):
                # Use your font.render(surface, text, color, size, pos)
                self.font.render(surface, msg, col, 12, (5, self.rect.y + 5 + (i * 12)))

    # Initialize it in main()
    console = Console(font)
    # Connect it to the engine
    engine.ctx['console'] = console

    #####################
    # -=Main Loop=-     #
    #####################

    while run:
        events = pygame.event.get()
        screen.fill((255, 255, 255))
        screen.blit(ed_bg, (0, 0))
        ox = (screen_size.current_w - window_size[0]) // 2
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > 255 / sensitivity:
            pygame.mouse.set_pos((255 / sensitivity, mouse_pos[1]))
        if mouse_pos[1] > 255 / sensitivity:
            pygame.mouse.set_pos((mouse_pos[0], 255 / sensitivity))
        mpos = mouse.hitbox.center

        for event in events:
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.KEYDOWN:
                    # EMERGENCY ESCAPE
                    if event.key == pygame.K_ESCAPE:
                        if engine.ctx['running']:
                            engine.ctx['running'] = False
                            print("Engine Stopped. Returning to Editor...")
                        else:
                            # If we aren't running, maybe Escape does something else?
                            pass

        if engine.ctx["running"]:
            mouse.set_state(0)
            engine.run_frame()
            console.draw(screen)
        else:
            if is_explorer:
                status = explorer.update(events, mouse)
                explorer.draw(screen, mouse)
                
                if status == "cancel":
                    is_explorer = False
                elif status == "ok":
                    if explorer.selected_file:
                        print(f"User confirmed file: {explorer.selected_file}")
                        try:
                            storage.add_image(explorer.selected_file, "new")
                        except Exception:
                            pass
                    is_explorer = False
                
                # Skip the rest of the editor logic while explorer is open
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
                    # If the user clicks outside or hits a close button (add this logic to storage)
                    # For now, let's allow pressing 'Escape' to close it for testing:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        is_storage = False
                    continue

                # Keyboard handling for editing input slots
                if event.type == pygame.KEYDOWN:
                    if input_block is not None:
                        consumed = input_block.handle_key(event)
                        if consumed:
                            if input_block.editing_index is None:
                                input_block = None
                                input_block_idx = None
                            continue

                # Mouse wheel handling
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
                        if input_block is None:
                            pass
                        else:
                            continue

                    # Scrollbar handle interaction
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
                                # FIX: Pass the 'btype' from the toolbox block (tb) to the new block
                                new_block = Block(tb.text, tb.color, (tb_rect.x, tb_rect.y), btype=tb.btype) 
                                
                                new_block.dragging = True
                                new_block.offset = [new_block.pos[0] - mpos[0], new_block.pos[1] - mpos[1]]
                                blocks.append(new_block)
                                active_block = new_block
                                spawned = True
                                hover_timers[idx] = None
                                break

                    if not spawned:
                        # Iterate reversed so we click top blocks first
                        for b in reversed(blocks):
                            idx = b.input_at(event.pos)
                            if idx is not None:
                                val = b.slots[idx]["value"]
                                if isinstance(val, Block):
                                    # 1. Pull it out
                                    active_block = val
                                    # 2. Clear the parent's slot
                                    b.slots[idx]["value"] = "" 
                                    # 3. Add it back to the main list so it's 'alive' again
                                    blocks.append(active_block)
                                    active_block.dragging = True
                                    break

                        for b in reversed(blocks):
                            
                            # 1. Check Input Slots first (so you can still edit text)
                            slot_hit = b.input_at(mpos)
                            if slot_hit is not None:
                                b.start_edit_input(slot_hit)
                                input_block = b
                                input_block_idx = slot_hit
                                # Bring to front
                                if b in blocks:
                                    blocks.remove(b)
                                    blocks.append(b)
                                break # Stop checking other blocks

                            # 2. FIX: Check dragging using the HEADER rect
                            # This prevents clicking the "hole" of an L-block
                            if b.get_header_rect().collidepoint(mpos):
                                active_block = b
                                
                                # Detach from previous parent (logic remains same)
                                for other in blocks:
                                    if other.child == b:
                                        other.child = None
                                    # FIX: Also detach from nested parent if dragging out
                                    if other.nested_child == b:
                                        other.nested_child = None
                                
                                if b.parent:
                                    if b.parent.child == b: b.parent.child = None
                                    if b.parent.nested_child == b: b.parent.nested_child = None
                                    b.parent = None
                                b.dragging = True
                                        
                                b.dragging = True
                                b.offset = [b.pos[0] - mpos[0], b.pos[1] - mpos[1]]
                                
                                # Bring to front
                                blocks.remove(b)
                                blocks.append(b)
                                break

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if active_block:
                        if active_block.get_rect().colliderect(trash_rect):
                            delete_chain(active_block, blocks)
                        else:
                            active_block.dragging = False
                            if active_block.try_snap(blocks):
                                blocks.remove(active_block)
                        
                            active_block = None

                        root = active_block
                        while any(other.child == root for other in blocks):
                            for other in blocks:
                                if other.child == root:
                                    root = other
                                    break

                        print(f"Current Stack Order: {' -> '.join(root.get_sequence())}")
                        active_block = None

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

            mouse.set_state(0)
            if active_block:
                if active_block.get_rect().colliderect(trash_rect):
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

            for b in blocks:
                b.update(mpos, blocks)

            if is_storage:
                # Only render storage if active
                storage.render(screen)
                # You might want a way to close it, like a small 'X' button or checking mpos
            elif is_menu:
                # Only run menu/block logic if storage is NOT open
                if not is_error:
                    if home_b.update(mouse):
                        run = False
                    if assets_b.update(mouse):
                        is_storage = True
                    
                    if play_b.update(mouse):
                        root = None
                        for b in blocks:
                            if b.parent is None: # Your logic to find the 'Start' block
                                root = b
                                break
                                
                        if root:
                            # 2. Compile it!
                            engine.compile(root)
                            engine.ctx['running'] = True
                            engine.ctx['pc'] = 0 # Reset program counter
                            print("Game Started!")

                    if not is_explorer:
                        b_hover(assets_b, assets_h, assets)
                        b_hover(home_b, home_h, home)
                        b_hover(play_b, play_h, play)

                        # Toolbox background
                        pygame.draw.rect(screen, (12, 46, 86), tb_view, border_radius=2)
                        inner = tb_view.inflate(-4, -4)
                        pygame.draw.rect(screen, (22, 66, 106), inner, border_radius=2)

                        # Scrollbar computation
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

                        # Clip to toolbox viewport
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
                            # A block is a ROOT if it is not owned by anyone else.
                            is_owned_as_child = any(other.child == b for other in blocks)
                            is_owned_as_nested = any(other.nested_child == b for other in blocks)
                            
                            if not is_owned_as_child and not is_owned_as_nested:
                                # This is the start of a script. 
                                # Calling stamp() here will trigger a single, clean recursive 
                                # pass through the entire nested and vertical tree.
                                b.stamp(screen)
                else:
                    font.render(screen, "ERROR 404", (255, 0, 0), 24, (30, 188))

                if not is_explorer:
                    # Tooltip
                    tooltip_to_show = None
                    tooltip_idx = None
                    now = pygame.time.get_ticks()
                    for idx, start in enumerate(hover_timers):
                        if start is not None and now - start >= HOVER_TOOLTIP_DELAY_MS:
                            tooltip_to_show = toolbox_blocks[idx].desc if hasattr(toolbox_blocks[idx], "desc") else toolbox_blocks[idx].text
                            tooltip_idx = idx
                            break

                    if tooltip_to_show is not None:
                        MAX_TIP_W = 140
                        pad_x, pad_y = 6, 6
                        lines = wrap_text(tooltip_to_show, MAX_TIP_W - pad_x * 2)
                        tw = 0
                        th = 0
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
                    explorer.update(events, mouse) # Use your mouse class
                    explorer.draw(screen, mouse)

        mouse.render(screen, sensitivity)

        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, (ox, 0))
        pygame.display.flip()
        clock.tick(FPS_CAP)
        pygame.display.set_caption(f"Floppy Player - FPS: {int(clock.get_fps())}")

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()