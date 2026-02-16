import pygame
import math
from font import *

def cut_surf(surf:pygame.Surface, pos:tuple, dim:tuple):
    rect = pygame.Rect(pos, dim)
    sub = pygame.Surface(dim, pygame.SRCALPHA)
    sub.blit(surf, (0, 0), rect)
    return sub

def lighter_tint(color, factor=0.6):
    # move each channel toward 255 by factor (0..1)
    return tuple(min(255, int(c + (255 - c) * factor)) for c in color)

def render_neck(surf, parts, height:int, width:int, pos:tuple):
    cp = pygame.transform.scale(parts[1], (width, height))
    ssu = pygame.Surface((width, 1));ssu.blit(parts[0], (0, 0)); ssu.blit(cp, (2, 0)); ssu.blit(parts[2], (width-2, 0))
    cp = pygame.transform.scale(ssu, (width, height))
    surf.blit(cp, pos)

class Block:
    """
    Block supports inline input slots written as [value] or [type:value] in the text.
    Real-time resizing while editing is supported — the block will resize as you type.
    """

    def __init__(self, text:str="example", color=(255, 0, 0), pos=(50, 50), btype="n"):
        self.btype = btype # "n" for normal, "l" for long/wrap, "o" for oval
        self.text = text
        self.color = color
        self.pos = [pos[0], pos[1]]
        self.child = None        # Block connected below
        self.nested_child = None # Block connected INSIDE (for "l" types)
        self.parent = None

        self.font = Font("Fonts/power clear.ttf", 12)
        self.dragging = False
        self.hovered = False
        self.offset = [0, 0]
        self.child = None
        
        # Load assets
        self.sprite = pygame.image.load("assets/block.png").convert_alpha()
        self.neck_sprite = pygame.image.load("assets/block_neck.png").convert_alpha()
        self.update_parts_color(self.color)

        # parse the text into parts: ("text", str) or ("slot", {"type":..., "value":...})
        self.template_parts = self._parse_text(self.text)

        # convenience list of slot dicts (references in template_parts)
        self.slots = [part[1] for part in self.template_parts if part[0] == "slot"]

        # layout helpers
        self.slot_rects = []  # rects relative to block top-left (updated in compute_layout)

        # editing state
        self.editing_index = None   # which slot index is being edited (workspace only)
        self.editing_text = ""      # current editing text
        self._caret_blink_ts = 0

        if self.btype == "o":
            self.corner_radius = 4
            self.padding_x = 5
            self.padding_y = 2

    def update_parts_color(self, new_color):
        temp_sprite = self.sprite.copy()
        pixel_array = pygame.PixelArray(temp_sprite)
        pixel_array.replace((255, 0, 0), new_color)
        pixel_array.close()

        self.parts = [
            cut_surf(temp_sprite, (0, 0), (2, 2)), cut_surf(temp_sprite, (0, 3), (2, 1)),
            cut_surf(temp_sprite, (0, 5), (2, 2)), cut_surf(temp_sprite, (3, 0), (1, 3)),
            cut_surf(temp_sprite, (3, 4), (1, 3)), cut_surf(temp_sprite, (0, 0), (2, 2)),
            cut_surf(temp_sprite, (5, 0), (5, 3)), cut_surf(temp_sprite, (7, 4), (1, 1)),
            cut_surf(temp_sprite, (5, 6), (5, 3)), cut_surf(temp_sprite, (11, 0), (2, 2)),
            cut_surf(temp_sprite, (11, 3), (2, 1)), cut_surf(temp_sprite, (11, 5), (2, 2))
        ]

        # precompute slot colors
        self.slot_fill = lighter_tint(new_color, 0.6)
        # border slightly darker than fill
        self.slot_border = tuple(max(0, int(c * 0.8)) for c in self.slot_fill)

        neck_array = pygame.PixelArray(self.neck_sprite)
        neck_array.replace((255, 0, 0), new_color)
        neck_array.close()

        self.neck_parts = [
            cut_surf(self.neck_sprite, (0, 0), (2, 1)),
            cut_surf(self.neck_sprite, (3, 0), (1, 1)),
            cut_surf(self.neck_sprite, (5, 0), (2, 1))
        ]
    
    def render_wrapper(self, display, x, y, total_w, content_h):
        # 1. Calculate nested height (Recursively)
        nested_h = 14 # Minimum height for an empty mouth
        if self.nested_child:
            curr = self.nested_child
            nested_h = 0
            while curr:
                nested_h += curr.get_size()[1] - 1 # -1 for overlap
                curr = curr.child
            nested_h += 8 # Extra padding at the bottom of the stack

        # 2. Draw the Neck (Left vertical connector)
        # The neck starts below the top bar and ends at the bottom bar
        neck_x = x
        neck_y = y + content_h 
        neck_w = 13  # Width of the left "pillar"
        
        # Use your render_neck helper, but ensure parts align
        # We pass 'nested_h' as the height of the distinct neck area
        render_neck(display, self.neck_parts, nested_h, neck_w, (neck_x, neck_y))
        
        # 3. Draw the Chunky Bottom Bar (The "Closer")
        bottom_y = neck_y + nested_h
        
        # A. Bottom-Left Corner (matches top-left style)
        display.blit(self.parts[2], (x, bottom_y)) 
        
        # B. The Horizontal "Floor" of the C-shape
        # We stretch the middle texture (part 7 usually)
        floor_w = total_w - 2 # slightly narrower than top
        floor_h = 8           # thickness of bottom bar
        mid_fill = pygame.transform.scale(self.parts[7], (floor_w, floor_h))
        display.blit(mid_fill, (x + 2, bottom_y))
        
        # C. Bottom-Right Cap
        display.blit(self.parts[11], (x + floor_w, bottom_y))
    
    def draw_oval_block(self, display, x, y):
        _, content_h, slot_rects, display_texts, (w, h) = self.compute_layout()

        radius = h // 2
        rect = pygame.Rect(x, y, w, h)

        # body
        pygame.draw.ellipse(display, self.color, rect)

        # outline
        pygame.draw.ellipse(display, (0, 0, 0), rect, 1)

        # render inline content (same logic as slots)
        cursor_x = x + radius // 2
        cursor_y = y + (h - content_h) // 2

        slot_index_counter = 0
        for part in self.template_parts:
            if part[0] == "text":
                self.font.render(display, part[1], (0, 0, 0), 12, (cursor_x, cursor_y))
                cursor_x += self.font.font.size(part[1])[0]
            else:
                self._render_inline_slot(
                    display, part, cursor_x, cursor_y, slot_index_counter
                )
                cursor_x += slot_rects[slot_index_counter].w + 4
                slot_index_counter += 1

    def _parse_text(self, text):
        """
        Parse text into list of ("text", str) and ("slot", {"type":..., "value":...}).
        Slot syntax: [value] or [type:value] where type is "number" or "string".
        If type omitted, attempt to autodetect numeric values.
        """
        parts = []
        i = 0
        cur = ""
        while i < len(text):
            c = text[i]
            if c == "[":
                if cur:
                    parts.append(("text", cur))
                    cur = ""
                j = text.find("]", i+1)
                if j == -1:
                    cur += c
                    i += 1
                    continue
                inside = text[i+1:j]
                if ":" in inside:
                    t, val = inside.split(":", 1)
                    t = t.strip().lower()
                    if t in ("num", "number", "n"):
                        stype = "number"
                    else:
                        stype = "string"
                    sval = val
                else:
                    sval = inside
                    try:
                        float(sval)
                        stype = "number"
                    except Exception:
                        stype = "string"
                parts.append(("slot", {"type": stype, "value": sval}))
                i = j + 1
            else:
                cur += c
                i += 1
        if cur:
            parts.append(("text", cur))
        return parts

    def _rebuild_text_from_parts(self):
        out = ""
        for part in self.template_parts:
            if part[0] == "text":
                out += part[1]
            else:
                out += "[" + str(part[1]["value"]) + "]"
        return out

    def compute_layout(self):
        """
        Compute layout for inline content:
        - total_content_w: width of inline text+slots
        - content_h: max content height
        - slot_rects: list of pygame.Rect relative to block top-left (x,y,w,h) for each slot
        - display_texts: list of strings that will be rendered inside each slot (uses editing buffer when applicable)
        """
        left_content_offset = 13 + 2  # matches stamp origin for inline content
        top_content_offset = 3

        min_slot_w = 16
        padding_x = 6
        padding_y = 2
        slot_spacing = 2

        total_x = 0
        content_h = 0
        slot_rects = []
        display_texts = []

        slot_index = 0
        for part in self.template_parts:
            if part[0] == "text":
                tw, th = self.font.font.size(part[1])
                total_x += tw
                content_h = max(content_h, th)
            else:
                slot_data = part[1]
                val = slot_data["value"]
                
                if isinstance(val, Block):
                    # The slot IS the block now
                    val.compute_layout() # Recursively update child
                    sw, sh = val.get_size()
                else:
                    # Standard text/empty slot logic
                    disp = str(val) if val is not None else ""
                    txt_w, txt_h = self.font.font.size(disp if disp != "" else " ")
                    sw = max(20, txt_w + 10) # Minimum width for empty slot
                    sh = max(txt_h + 4, 15)

                slot_rects.append(pygame.Rect(total_x, top_content_offset, sw, sh))
                total_x += sw + 5
                content_h = max(content_h, sh)

        total_content_w = total_x

        # final block dims (preserve original padding logic)
        w = total_content_w + 10
        total_w = 13 + w + 2
        h = content_h + 3
        total_h = h + 2

        return total_content_w, content_h, slot_rects, display_texts, (int(total_w), int(total_h))

    def get_size(self):
        _, content_h, slot_rects, _, (total_w, _) = self.compute_layout()
        self.slot_rects = slot_rects
        
        # Base height of the block's top bar
        my_h = content_h + 4 
        
        if self.btype == "l":
            # Calculate height of the ENTIRE nested chain
            nested_h = 14 # Minimum "empty" mouth height
            
            if self.nested_child:
                nested_h = 0
                curr = self.nested_child
                while curr:
                    # Add current block's height
                    # overlap (-1) is crucial for seamless look
                    nested_h += curr.get_size()[1] - 1 
                    curr = curr.child
                
                # Add a little padding so the bottom bar doesn't touch the last block
                nested_h += 4

            # Total L-Height = Top Bar + Inner Chain + Bottom Bar (approx 8px)
            total_h = my_h + nested_h + 12
        else:
            total_h = my_h

        return (total_w, total_h)

    def get_rect(self):
        w, h = self.get_size()
        return pygame.Rect(int(self.pos[0]), int(self.pos[1]), w, h)
    
    def get_header_rect(self):
        """Returns the rect of just the top 'handle' of the block."""
        w, _ = self.get_size()
        h = self.compute_layout()[1] + 8
        return pygame.Rect(self.pos[0], self.pos[1], w, h)

    def get_sequence(self):
        sequence = [self.text]
        if self.child:
            sequence.extend(self.child.get_sequence())
        return sequence

    def update(self, mouse_pos, blocks):
        # 1. Update self
        if self.dragging:
            self.pos[0] = int(mouse_pos[0] + self.offset[0])
            self.pos[1] = int(mouse_pos[1] + self.offset[1])
        
        # 2. Lock Substack (Inside)
        if self.nested_child:
            header_h = self.compute_layout()[1] + 5
            self.nested_child.pos[0] = self.pos[0] + 13
            self.nested_child.pos[1] = self.pos[1] + header_h
            self.nested_child.update(mouse_pos, blocks) # Recurse

        # 3. Lock Chain (Below)
        if self.child:
            self.child.pos[0] = self.pos[0]
            self.child.pos[1] = self.pos[1] + self.get_size()[1] - 1
            self.child.update(mouse_pos, blocks) # Recurse
    
    def try_snap_into_slot(self, blocks):
        if self.btype != "o":
            return

        for other in blocks:
            idx = other.input_at(self.pos)
            if idx is not None:
                other.slots[idx]["value"] = self
                self.parent = other
                return

    def try_snap(self, blocks):
        self.dragging = False

        # 1. Try snapping into an Oval Slot first
        if self.btype == "o":
            for other in blocks:
                if other == self: continue
                idx = other.input_at(self.pos)
                if idx is not None:
                    other.slots[idx]["value"] = self
                    self.parent = other
                    return True # Signal success to remove from main list
            return False

        for other in blocks:
            if other == self: continue
            
            # Get landmarks
            header_h = other.compute_layout()[1] + 5
            full_h = other.get_size()[1]
            
            # --- LANDMARK A: THE MOUTH (Inner Snap) ---
            if other.btype == "l":
                mouth_pos = (other.pos[0] + 13, other.pos[1] + header_h)
                if math.hypot(self.pos[0] - mouth_pos[0], self.pos[1] - mouth_pos[1]) < 25:
                    # If someone is already in the mouth, push them to the end of our new chain
                    if other.nested_child:
                        self.get_last_in_chain().child = other.nested_child
                        other.nested_child.parent = self.get_last_in_chain()
                    
                    other.nested_child = self
                    self.parent = other
                    self.pos = list(mouth_pos)
                    return

            # --- LANDMARK B: THE FLOOR (Bottom Snap) ---
            floor_pos = (other.pos[0], other.pos[1] + full_h - 1)
            if math.hypot(self.pos[0] - floor_pos[0], self.pos[1] - floor_pos[1]) < 25:
                if other.child:
                    self.get_last_in_chain().child = other.child
                    other.child.parent = self.get_last_in_chain()
                
                other.child = self
                self.parent = other
                self.pos = list(floor_pos)
                return

    def get_last_in_chain(self):
        curr = self
        while curr.child:
            curr = curr.child
        return curr

    def input_at(self, pos):
        """Returns the index of the slot at the given global position."""
        # Convert global mouse pos to local block-space
        local_x = pos[0] - self.pos[0]
        local_y = pos[1] - self.pos[1]
        
        for i, rect in enumerate(self.slot_rects):
            if rect.collidepoint(local_x, local_y):
                return i
        return None

    def start_edit_input(self, slot_index):
        if slot_index is None or slot_index < 0 or slot_index >= len(self.slots):
            return
        self.editing_index = slot_index
        curr = self.slots[slot_index]["value"]
        self.editing_text = str(curr) if curr is not None else ""
        self._caret_blink_ts = pygame.time.get_ticks()

    def stop_edit_input(self, commit=True):
        if self.editing_index is not None and commit:
            slot = self.slots[self.editing_index]
            
            if slot["type"] == "number":
                # 1. ADD THIS: If it's a variable, keep it as text and skip float conversion
                if self.editing_text.startswith("var:"):
                    slot["value"] = self.editing_text
                else:
                    # 2. Existing number logic
                    try:
                        val = float(self.editing_text) if (self.editing_text != "" and self.editing_text not in ["-", "."]) else None
                        if val is not None:
                            if float(val).is_integer():
                                slot["value"] = str(int(val))
                            else:
                                slot["value"] = str(val)
                        else:
                            slot["value"] = ""
                    except Exception:
                        # invalid numeric -> keep previous value
                        pass
            else:
                slot["value"] = self.editing_text

            # reflect change into template_parts and text
            si = 0
            new_parts = []
            for part in self.template_parts:
                if part[0] == "text":
                    new_parts.append(part)
                else:
                    if si == self.editing_index:
                        new_parts.append(("slot", {"type": slot["type"], "value": slot["value"]}))
                    else:
                        new_parts.append(("slot", {"type": part[1]["type"], "value": part[1]["value"]}))
                    si += 1
            self.template_parts = new_parts
            self.slots = [part[1] for part in self.template_parts if part[0] == "slot"]
            self.text = self._rebuild_text_from_parts()

        # clear editing
        self.editing_index = None
        self.editing_text = ""

    def handle_key(self, event):
        """
        Handle KEYDOWN event while editing. Returns True if consumed.
        """
        if self.editing_index is None:
            return False
        slot = self.slots[self.editing_index]
        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self.stop_edit_input(commit=True)
            return True
        if event.key == pygame.K_ESCAPE:
            self.stop_edit_input(commit=False)
            return True
        if event.key == pygame.K_BACKSPACE:
            self.editing_text = self.editing_text[:-1]
            return True
        if event.unicode and event.unicode.isprintable():
            ch = event.unicode
            if slot["type"] == "number":
                # 1. Check if we are currently typing a variable
                is_var_mode = self.editing_text.startswith("var:")
                
                # 2. If typing a variable, allow almost anything (letters, numbers, underscores)
                if is_var_mode:
                    if ch.isalnum() or ch in "_:":
                        self.editing_text += ch
                        return True
                
                # 3. Allow starting the variable prefix with 'v'
                if ch == "v" and self.editing_text == "":
                    self.editing_text = "var:"
                    return True

                # 4. Standard number logic
                if ch.isdigit():
                    self.editing_text += ch
                    return True
                if ch == "." and "." not in self.editing_text:
                    self.editing_text += ch
                    return True
                if ch == "-" and self.editing_text == "":
                    self.editing_text += ch
                    return True
                
                return False
            else:
                # String slots allow everything
                self.editing_text += ch
                return True
        return False

    def _stamp_at(self, display, pos):
        # Use original visual layout but inline content width computed from compute_layout
        x, y = pos
        tw, th, slot_rects, content_h, (total_w, h) = self.compute_layout()
        total_content_w, content_h, slot_rects, display_texts, (w, h) = self.compute_layout()
        total_content_w += 23

        # store slot rects for input_at if needed
        self.slot_rects = slot_rects

        # Glow (as in original)
        if self.hovered or self.dragging:
            glow_rect = pygame.Rect(int(x), int(y) + 1, int(w)+18, int(h)+4).inflate(2, 2)
            glow_surf = pygame.Surface((glow_rect.w, glow_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 255, 255, 100), (0, 0, glow_rect.w, glow_rect.h), border_radius=3)
            display.blit(glow_surf, (glow_rect.x - 2, glow_rect.y - 2))

        # draw left/top parts
        display.blit(self.parts[0], (x, y))
        cp = pygame.transform.scale(self.parts[3], (6, self.parts[3].get_height()))
        display.blit(cp, (x + 2, y))
        display.blit(self.parts[6], (x + 8, y))

        # draw top middle scaled to total_content_w
        cp = pygame.transform.scale(self.parts[3], (total_content_w, self.parts[3].get_height()))
        display.blit(cp, (x + 13, y))
        display.blit(self.parts[9], (x + 13 + total_content_w, y))
        cp = pygame.transform.scale(self.parts[1], (self.parts[1].get_width(), h - 1))
        display.blit(cp, (x, y + 2))
        display.blit(self.parts[2], (x, y + h))
        cp = pygame.transform.scale(self.parts[4], (6, self.parts[4].get_height()))
        display.blit(cp, (x + 2, y + h - 1))
        display.blit(self.parts[8], (x + 8, y + h + 1))
        cp = pygame.transform.scale(self.parts[4], (total_content_w, self.parts[4].get_height()))
        display.blit(cp, (x + 13, y + h - 1))
        display.blit(self.parts[11], (x + 13 + total_content_w, y + h))
        cp = pygame.transform.scale(self.parts[10], (self.parts[10].get_width(), h - 1))
        display.blit(cp, (x + 13 + total_content_w, y + 2))
        cp = pygame.transform.scale(self.parts[7], (11 + total_content_w, h - 2))
        display.blit(cp, (x + 2, y + 3))

        # Render inline content at (x + 13 + 2, y + 3)
        cursor_x = x + 13 + 2
        cursor_y = y + 3
        slot_index_counter = 0

        for part in self.template_parts:
            if part[0] == "text":
                self.font.render(display, part[1], (0,0,0), 12, (cursor_x, cursor_y))
                s_w, s_h = self.font.font.size(part[1])
                cursor_x += s_w
            else:
                # displayed value uses editing_text if active for this slot
                if self.editing_index == slot_index_counter:
                    display_text = self.editing_text
                    now = pygame.time.get_ticks()
                    if now - self._caret_blink_ts >= 500:
                        self._caret_blink_ts = now
                    show_caret = ((now // 500) % 2) == 0
                else:
                    val = part[1]["value"]
                    to_disp = True
                    if isinstance(val, Block):
                        # Instead of drawing a rect, tell the nested block to draw itself here
                        val.stamp_at(display, (cursor_x, cursor_y))
                        cursor_x += val.get_size()[0] + 2
                        to_disp = False
                    if to_disp:
                        display_text = str(val) if val is not None else ""
                    else:
                        display_text = ""
                    show_caret = False

                measure_text = display_text if display_text != "" else "0"
                txt_w, txt_h = self.font.font.size(measure_text)
                padding_x = 6
                padding_y = 2
                sw = max(16, txt_w + padding_x * 2)
                sh = max(txt_h + padding_y * 2, 12)
                slot_x = cursor_x
                slot_y = cursor_y
                slot_rect = pygame.Rect(slot_x, slot_y, sw, sh)
                pygame.draw.rect(display, self.slot_fill, slot_rect, border_radius=4)
                pygame.draw.rect(display, self.slot_border, slot_rect, width=1, border_radius=4)

                # draw text centered
                s_w2, s_h2 = self.font.font.size(display_text if display_text != "" else " ")
                txt_x = slot_x + (sw - s_w2) // 2
                txt_y = slot_y + (sh - s_h2) // 2
                self.font.render(display, display_text, (0,0,0), 12, (txt_x, txt_y))

                # caret when editing
                if self.editing_index == slot_index_counter and show_caret:
                    caret_x = txt_x + s_w2 + 1
                    caret_y1 = txt_y
                    caret_y2 = txt_y + s_h2
                    pygame.draw.line(display, (0,0,0), (caret_x, caret_y1), (caret_x, caret_y2), 1)

                cursor_x += sw + 2
                slot_index_counter += 1

        # 2. WRAPPER RENDERING (The C-shape)
        if self.btype == "l":
            self.render_wrapper(display, x, y, total_w, content_h)
            
            # --- FIX: STRICT RECURSION ---
            # We ONLY call the immediate nested child. 
            # We do NOT loop through curr = curr.child here.
            if self.nested_child:
                # The nested child will draw itself AND its own children automatically.
                # We simply tell it where the "mouth" starts.
                nested_y = y + content_h + 5
                self.nested_child.stamp_at(display, (x + 13, nested_y))

        # 3. CHAIN RENDERING (The block BELOW)
        # This is the standard "Next" block in the sequence.
        if self.child:
            # We don't need stamp_at here because self.child.pos is 
            # already kept perfectly in sync by the update() function.
            self.child.stamp(display)

    def stamp(self, display):
        if self.btype == "o":
            self.draw_oval_block(display, self.pos[0], self.pos[1])
            return

        self._stamp_at(display, self.pos)

    def stamp_at(self, display, pos):
        # render at explicit pos (toolbox rendering)
        # toolbox templates are not editable; ensure editing_index cleared for templates
        prev_edit = (self.editing_index, self.editing_text)
        self.editing_index = None
        self.editing_text = ""
        self._stamp_at(display, pos)
        self.editing_index, self.editing_text = prev_edit

    def compile_expr(self):
        return {
            "type": "expr",
            "opcode": self.text.split("[")[0].strip(),
            "params": self.get_slot_values()
        }
    
    def get_slot_values(self):
        values = []
        for slot in self.slots:
            val = slot["value"]
            if isinstance(val, Block):  # O-Block detected
                values.append(val.compile_expr())
            else:
                values.append(val)
        return values
    
    def to_dict(self):
        """
        Recursively converts the block chain into a logic tree for the interpreter.
        """
        # 1. Base data
        data = {
            "opcode": self.text.split('[')[0].strip(), # e.g., "Repeat"
            "params": self.get_slot_values(),          # e.g., [10]
            "next": None,                              # The block attached below
            "substack": None                           # The blocks inside (if L-block)
        }

        # 2. Recursively grab the Nested Stack (for L-blocks)
        if self.btype == "l" and self.nested_child:
            data["substack"] = self.nested_child.to_dict()

        # 3. Recursively grab the Next Block
        if self.child:
            data["next"] = self.child.to_dict()

        return data