import pygame
import math
from font import *

def cut_surf(surf:pygame.Surface, pos:tuple, dim:tuple):
    rect = pygame.Rect(pos, dim)
    sub = pygame.Surface(dim, pygame.SRCALPHA)
    sub.blit(surf, (0, 0), rect)
    return sub

def lighter_tint(color, factor=0.6):
    return tuple(min(255, int(c + (255 - c) * factor)) for c in color)

def render_neck(surf, parts, height:int, width:int, pos:tuple):
    cp = pygame.transform.scale(parts[1], (width, height))
    ssu = pygame.Surface((width, 1));ssu.blit(parts[0], (0, 0)); ssu.blit(cp, (2, 0)); ssu.blit(parts[2], (width-2, 0))
    cp = pygame.transform.scale(ssu, (width, height))
    surf.blit(cp, pos)

class Block:
    def __init__(self, text:str="example", color=(255, 0, 0), pos=(50, 50), btype="n"):
        self.btype = btype 
        self.text = text
        self.color = color
        self.pos = [pos[0], pos[1]]
        self.child = None        
        self.nested_child = None 
        self.parent = None

        self.font = Font("Fonts/power clear.ttf", 12)
        self.dragging = False
        self.hovered = False
        self.offset = [0, 0]
        
        self.sprite = pygame.image.load("assets/block.png").convert_alpha()
        self.neck_sprite = pygame.image.load("assets/block_neck.png").convert_alpha()
        self.update_parts_color(self.color)

        self.template_parts = self._parse_text(self.text)
        self.slots = [part[1] for part in self.template_parts if part[0] == "slot"]
        self.slot_rects = []  

        self.editing_index = None   
        self.editing_text = ""      
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

        self.slot_fill = lighter_tint(new_color, 0.6)
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
        nested_h = 14 
        if self.nested_child:
            curr = self.nested_child
            nested_h = 0
            visited = set() # CYCLE PREVENTION
            while curr and curr not in visited:
                visited.add(curr)
                nested_h += curr.get_size()[1] - 1 
                curr = curr.child
            nested_h += 8 

        neck_x = x
        neck_y = y + content_h 
        neck_w = 13  
        
        render_neck(display, self.neck_parts, nested_h, neck_w, (neck_x, neck_y))
        
        bottom_y = neck_y + nested_h
        display.blit(self.parts[2], (x, bottom_y)) 
        
        floor_w = total_w - 2 
        floor_h = 8           
        mid_fill = pygame.transform.scale(self.parts[7], (floor_w, floor_h))
        display.blit(mid_fill, (x + 2, bottom_y))
        display.blit(self.parts[11], (x + floor_w, bottom_y))
    
    def draw_oval_block(self, display, x, y):
        _, content_h, slot_rects, _, (total_w, total_h) = self.compute_layout()
        rect = pygame.Rect(x, y, total_w, total_h)
        pygame.draw.rect(display, self.color, rect, border_radius=total_h//2)
        pygame.draw.rect(display, (0, 0, 0), rect, width=1, border_radius=total_h//2)

        cursor_x = x + 15 
        cursor_y = y + 3
        
        slot_index_counter = 0
        for part in self.template_parts:
            if part[0] == "text":
                self.font.render(display, part[1], (0, 0, 0), 12, (cursor_x, cursor_y))
                tw, _ = self.font.font.size(part[1])
                cursor_x += tw
            else:
                slot_data = part[1]
                val = slot_data["value"]
                
                if isinstance(val, Block):
                    nested_size = val.get_size()
                    val.stamp_at(display, (cursor_x, y + (total_h - nested_size[1])//2))
                    cursor_x += nested_size[0] + 5
                else:
                    display_text = str(val) if (val != "") else str(slot_data.get("default", ""))
                    txt_w, txt_h = self.font.font.size(display_text if display_text != "" else " ")
                    
                    sw = max(20, txt_w + 10)
                    sh = max(txt_h + 4, 15)
                    
                    s_rect = pygame.Rect(cursor_x, cursor_y, sw, sh)
                    pygame.draw.rect(display, self.slot_fill, s_rect, border_radius=4)
                    
                    tx = cursor_x + (sw - txt_w) // 2
                    ty = cursor_y + (sh - txt_h) // 2
                    self.font.render(display, display_text, (0, 0, 0), 12, (tx, ty))
                    cursor_x += sw + 5
                slot_index_counter += 1

    def _parse_text(self, text):
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
                parts.append(("slot", {"type": stype, "value": sval, "default": sval}))
                i = j + 1
            else:
                cur += c
                i += 1
        if cur:
            parts.append(("text", cur))
        return parts

    def _rebuild_text_from_parts(self):
        res = ""
        for p_type, p_val in self.template_parts:
            if p_type == "text":
                res += p_val
            elif p_type == "slot":
                val = p_val["value"]
                if isinstance(val, Block):
                    res += f"({val._rebuild_text_from_parts()})"
                else:
                    res += f"[{val}]"
        return res

    def compute_layout(self):
        left_content_offset = 13 + 2 
        top_content_offset = 3
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
                    val.compute_layout() 
                    sw, sh = val.get_size()
                else:
                    disp = str(val) if (val is not None and val != "") else str(slot_data.get("default", ""))
                    txt_w, txt_h = self.font.font.size(disp if disp != "" else " ")
                    sw = max(20, txt_w + 10) 
                    sh = max(txt_h + 4, 15)

                slot_rects.append(pygame.Rect(total_x, top_content_offset, sw, sh))
                total_x += sw + 5
                content_h = max(content_h, sh)

        total_content_w = total_x
        w = total_content_w + 10
        total_w = 13 + w + 2
        h = content_h + 3
        total_h = h + 2

        return total_content_w, content_h, slot_rects, display_texts, (int(total_w), int(total_h))

    def get_size(self):
        _, content_h, slot_rects, _, (total_w, total_h) = self.compute_layout()
        self.slot_rects = slot_rects
        
        if self.btype == "o":
            return (total_w, total_h)
        
        my_h = content_h + 4 
        if self.btype == "l":
            nested_h = 14 
            if self.nested_child:
                nested_h = 0
                curr = self.nested_child
                visited = set() # CYCLE PREVENTION
                while curr and curr not in visited:
                    visited.add(curr)
                    nested_h += curr.get_size()[1] - 1 
                    curr = curr.child
                nested_h += 4
            total_h = my_h + nested_h + 12
        else:
            total_h = my_h

        return (total_w, total_h)
    
    def get_header_rect(self):
        w, _ = self.get_size()
        h = self.compute_layout()[1] + 8
        return pygame.Rect(self.pos[0], self.pos[1], w, h)

    def get_rect(self):
        w, _ = self.get_size()
        _, content_h, _, _, _ = self.compute_layout()
        header_h = content_h + 8 
        return pygame.Rect(int(self.pos[0]), int(self.pos[1]), w, header_h)

    def get_toolbox_height(self):
        if self.btype == "o":
            return self.get_size()[1]
        _, content_h, _, _, _ = self.compute_layout()
        header_h = content_h + 8 
        if self.btype == "l":
            return header_h + 14 + 8
        return header_h

    def get_sequence(self):
        sequence = [self._rebuild_text_from_parts()]
        if self.child:
            sequence.extend(self.child.get_sequence())
        return sequence

    def update(self, mouse_pos, blocks):
        if self.dragging:
            self.pos[0] = int(mouse_pos[0] + self.offset[0])
            self.pos[1] = int(mouse_pos[1] + self.offset[1])
        
        # 1. Handle Mouth Snapping (L-Blocks)
        if self.nested_child:
            if not self.nested_child.dragging: 
                header_h = self.compute_layout()[1] + 5
                self.nested_child.pos[0] = self.pos[0] + 13
                self.nested_child.pos[1] = self.pos[1] + header_h
            self.nested_child.update(mouse_pos, blocks)

        # 2. Handle Vertical Snapping (N-Blocks)
        if self.child:
            if not self.child.dragging: 
                self.child.pos[0] = self.pos[0]
                self.child.pos[1] = self.pos[1] + self.get_size()[1] - 1
            self.child.update(mouse_pos, blocks)

        # 3. FIX: Handle Oval Blocks in Slots (Synchronize their pos for interaction)
        total_content_w, content_h, slot_rects, _, _ = self.compute_layout()
        start_x = self.pos[0] + 15
        start_y = self.pos[1] + 3
        
        slot_idx = 0
        current_x = start_x
        for part in self.template_parts:
            if part[0] == "text":
                tw, _ = self.font.font.size(part[1])
                current_x += tw
            else:
                val = self.slots[slot_idx]["value"]
                if isinstance(val, Block):
                    if not val.dragging:
                        # Sync the nested block's internal pos to the slot's world pos
                        # This fixes the "unclickable/ghost" interaction bug
                        val.pos[0] = current_x
                        val.pos[1] = start_y + (content_h - val.get_size()[1]) // 2
                    val.update(mouse_pos, blocks)
                
                # Advance layout cursor
                sw = slot_rects[slot_idx].width
                current_x += sw + 5
                slot_idx += 1
    
    def is_ancestor_of(self, target):
        """ Safety check to ensure a block never tries to snap to its own child/descendant. """
        if self == target: 
            return True
            
        curr = self.child
        visited = set()
        while curr and curr not in visited:
            if curr == target: return True
            visited.add(curr)
            curr = curr.child
            
        curr = self.nested_child
        visited = set()
        while curr and curr not in visited:
            if curr == target: return True
            visited.add(curr)
            curr = curr.child
            
        for slot in self.slots:
            val = slot["value"]
            if isinstance(val, Block):
                if val.is_ancestor_of(target): return True
        return False

    def get_last_in_chain(self):
        curr = self
        visited = set()
        while curr.child and curr not in visited:
            visited.add(curr)
            curr = curr.child
            
        # Sever any accidental cycles physically
        if curr.child and curr.child in visited:
            curr.child = None 
            
        return curr

    def get_all_blocks_in_chain(self):
        """Returns a list containing this block and all its nested/vertical children."""
        results = [self]
        if self.child:
            results.extend(self.child.get_all_blocks_in_chain())
        if self.nested_child:
            results.extend(self.nested_child.get_all_blocks_in_chain())
        for slot in self.slots:
            if isinstance(slot["value"], Block):
                results.extend(slot["value"].get_all_blocks_in_chain())
        return results

    def get_block_body_height(self):
        _, content_h, _, _, _ = self.compute_layout()
        return content_h + 8

    def try_snap(self, blocks):
        self.dragging = False
        
        # 1. PREPARATION: Identify all potential target blocks in the world
        # We exclude the entire dragging chain (self and all descendants) to prevent cycles
        all_potential_targets = []
        for root in blocks:
            all_potential_targets.extend(root.get_all_blocks_in_chain())
            
        my_chain = self.get_all_blocks_in_chain()
        targets = [b for b in all_potential_targets if b not in my_chain]

        # 2. OVAL BLOCK SNAPPING (Slot Insertion/Replacement)
        if self.btype == "o":
            for other in targets:
                # Use the center of the oval for hit detection
                w, h = self.get_size()
                center_pos = (self.pos[0] + w // 2, self.pos[1] + h // 2)
                
                idx = other.input_at(center_pos)
                if idx is not None:
                    # Safety: Clear current parent if we were already attached
                    if self.parent:
                        if self.parent.child == self: self.parent.child = None
                        if hasattr(self.parent, 'nested_child') and self.parent.nested_child == self: 
                            self.parent.nested_child = None
                    
                    # Replacement logic: If the slot is occupied, unplug the old block
                    old_val = other.slots[idx]["value"]
                    if isinstance(old_val, Block):
                        old_val.parent = None
                        if old_val not in blocks: blocks.append(old_val)
                    
                    other.slots[idx]["value"] = self
                    self.parent = other
                    return True 
            
            # CRITICAL SAFETY: If an O-block misses a slot, it exits here.
            # It will NEVER run the vertical snapping code below.
            return False

        # 3. VERTICAL & MOUTH SNAPPING
        SNAP_DIST = 25
        for other in targets:
            
            # ---> THE BOUNCER: Nothing is allowed to snap vertically to an O-block!
            if other.btype == "o":
                continue

            # FIX: Use the individual block's body height
            block_body_h = other.get_block_body_height()
            
            # --- LANDMARK A: THE MOUTH (L-Blocks) ---
            if other.btype == "l":
                mouth_pos = (other.pos[0] + 13, other.pos[1] + block_body_h)
                if math.hypot(self.pos[0] - mouth_pos[0], self.pos[1] - mouth_pos[1]) < SNAP_DIST:
                    # Clean up old parent
                    if self.parent:
                        if self.parent.child == self: self.parent.child = None
                        if self.parent.nested_child == self: self.parent.nested_child = None

                    # Mid-chain insertion: If 'other' has a mouth-child, push it to our tail
                    if other.nested_child:
                        tail = self.get_last_in_chain()
                        tail.child = other.nested_child
                        other.nested_child.parent = tail
                    
                    other.nested_child = self
                    self.parent = other
                    self.pos = list(mouth_pos)
                    return True

            # --- LANDMARK B: THE FLOOR (Snap current block under target) ---
            floor_pos = (other.pos[0], other.pos[1] + block_body_h - 1)
            if math.hypot(self.pos[0] - floor_pos[0], self.pos[1] - floor_pos[1]) < SNAP_DIST:
                if self.parent:
                    if self.parent.child == self: self.parent.child = None
                    if hasattr(self.parent, 'nested_child') and self.parent.nested_child == self: 
                        self.parent.nested_child = None

                # Mid-chain insertion: If 'other' has a child, it now becomes our tail's child
                if other.child:
                    tail = self.get_last_in_chain()
                    tail.child = other.child
                    other.child.parent = tail
                
                other.child = self
                self.parent = other
                self.pos = list(floor_pos)
                return True

            # (LANDMARK C HAS BEEN PURPOSEFULLY DELETED TO PREVENT DISAPPEARING BUGS)
                
        return False

    def input_at(self, pos):
        total_content_w, content_h, slot_rects, _, (w, h) = self.compute_layout()
        start_x = self.pos[0] + (15 if self.btype != "o" else 15)
        start_y = self.pos[1] + 3
        slot_index = 0
        current_x = start_x

        for part in self.template_parts:
            if part[0] == "text":
                tw, _ = self.font.font.size(part[1])
                current_x += tw
            else:
                rect_dim = slot_rects[slot_index]
                global_slot_rect = pygame.Rect(current_x, start_y, rect_dim.width, rect_dim.height)
                
                if global_slot_rect.collidepoint(pos):
                    if not isinstance(self.slots[slot_index]["value"], Block):
                        return slot_index
                
                current_x += rect_dim.width + 5 
                slot_index += 1
        return None

    def start_edit_input(self, slot_index):
        if slot_index is None or slot_index < 0 or slot_index >= len(self.slots): return
        self.editing_index = slot_index
        curr = self.slots[slot_index]["value"]
        self.editing_text = str(curr) if (curr is not None and not isinstance(curr, Block)) else ""
        self._caret_blink_ts = pygame.time.get_ticks()

    def stop_edit_input(self, commit=True):
        if self.editing_index is not None and commit:
            slot = self.slots[self.editing_index]
            if slot["type"] == "number":
                if self.editing_text.startswith("var:"):
                    slot["value"] = self.editing_text
                else:
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
                        pass
            else:
                slot["value"] = self.editing_text

            si = 0
            new_parts = []
            for part in self.template_parts:
                if part[0] == "text":
                    new_parts.append(part)
                else:
                    if si == self.editing_index:
                        new_parts.append(("slot", {"type": slot["type"], "value": slot["value"], "default": slot.get("default", slot["value"])}))
                    else:
                        new_parts.append(("slot", {"type": part[1]["type"], "value": part[1]["value"], "default": part[1].get("default", part[1]["value"])}))
                    si += 1
            self.template_parts = new_parts
            self.slots = [part[1] for part in self.template_parts if part[0] == "slot"]
            self.text = self._rebuild_text_from_parts()

        self.editing_index = None
        self.editing_text = ""

    def handle_key(self, event):
        if self.editing_index is None: return False
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
                is_var_mode = self.editing_text.startswith("var:")
                if is_var_mode:
                    if ch.isalnum() or ch in "_:":
                        self.editing_text += ch
                        return True
                if ch == "v" and self.editing_text == "":
                    self.editing_text = "var:"
                    return True
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
                self.editing_text += ch
                return True
        return False

    def get_block_at(self, pos):
        for slot in self.slots:
            if isinstance(slot["value"], Block):
                found = slot["value"].get_block_at(pos)
                if found: return found

        if self.nested_child:
            found = self.nested_child.get_block_at(pos)
            if found: return found
            
        if self.child:
            found = self.child.get_block_at(pos)
            if found: return found

        if self.get_rect().collidepoint(pos):
            return self
            
        return None

    def _stamp_at(self, display, pos):
        x, y = pos
        tw, th, slot_rects, content_h, (total_w, h) = self.compute_layout()
        total_content_w, content_h, slot_rects, display_texts, (w, h) = self.compute_layout()
        total_content_w += 23

        self.slot_rects = slot_rects

        if self.hovered or self.dragging:
            glow_rect = pygame.Rect(int(x), int(y) + 1, int(w)+18, int(h)+4).inflate(2, 2)
            glow_surf = pygame.Surface((glow_rect.w, glow_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 255, 255, 100), (0, 0, glow_rect.w, glow_rect.h), border_radius=3)
            display.blit(glow_surf, (glow_rect.x - 2, glow_rect.y - 2))

        display.blit(self.parts[0], (x, y))
        cp = pygame.transform.scale(self.parts[3], (6, self.parts[3].get_height()))
        display.blit(cp, (x + 2, y))
        display.blit(self.parts[6], (x + 8, y))

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

        cursor_x = x + 13 + 2
        cursor_y = y + 3
        slot_index_counter = 0

        for part in self.template_parts:
            if part[0] == "text":
                self.font.render(display, part[1], (0,0,0), 12, (cursor_x, cursor_y))
                s_w, s_h = self.font.font.size(part[1])
                cursor_x += s_w
            else:
                slot_data = part[1]
                val = slot_data["value"]
                
                if self.editing_index == slot_index_counter:
                    display_text = self.editing_text
                    now = pygame.time.get_ticks()
                    if now - self._caret_blink_ts >= 500:
                        self._caret_blink_ts = now
                    show_caret = ((now // 500) % 2) == 0
                    should_render_slot = True
                else:
                    if isinstance(val, Block):
                        val.stamp_at(display, (cursor_x, cursor_y))
                        cursor_x += val.get_size()[0] + 2
                        should_render_slot = False
                        display_text = ""
                        show_caret = False
                    else:
                        display_text = str(val) if (val is not None and val != "") else str(slot_data.get("default", ""))
                        should_render_slot = True
                        show_caret = False

                if should_render_slot:
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

                    s_w2, s_h2 = self.font.font.size(display_text if display_text != "" else " ")
                    txt_x = slot_x + (sw - s_w2) // 2
                    txt_y = slot_y + (sh - s_h2) // 2
                    self.font.render(display, display_text, (0,0,0), 12, (txt_x, txt_y))

                    if self.editing_index == slot_index_counter and show_caret:
                        caret_x = txt_x + s_w2 + 1
                        caret_y1 = txt_y
                        caret_y2 = txt_y + s_h2
                        pygame.draw.line(display, (0,0,0), (caret_x, caret_y1), (caret_x, caret_y2), 1)

                    cursor_x += sw + 2
                    slot_index_counter += 1

        if self.btype == "l":
            self.render_wrapper(display, x, y, total_w, content_h)
            if self.nested_child:
                nested_y = y + content_h + 5
                self.nested_child.stamp_at(display, (x + 13, nested_y))

        if self.child:
            self.child.stamp(display)

    def stamp(self, display):
        if self.btype == "o":
            self.draw_oval_block(display, self.pos[0], self.pos[1])
            return
        self._stamp_at(display, self.pos)

    def stamp_at(self, display, pos):
        prev_edit = (self.editing_index, self.editing_text)
        self.editing_index = None
        self.editing_text = ""
        
        if self.btype == "o":
            self.draw_oval_block(display, pos[0], pos[1])
        else:
            self._stamp_at(display, pos)
            
        self.editing_index, self.editing_text = prev_edit

    def compile_expr(self):
        raw_text = self.text.split("[")[0]
        opcode = raw_text.replace("(", "").replace(")", "").strip()
        if opcode == "":
            if "+" in self.text: opcode = "+"
            elif "-" in self.text: opcode = "-"
            elif "*" in self.text: opcode = "*"
            elif "/" in self.text: opcode = "/"
            elif "%" in self.text: opcode = "%"
            elif "=" in self.text: opcode = "="
            elif ">" in self.text: opcode = ">"
            elif "<" in self.text: opcode = "<"
            elif ">=" in self.text: opcode = ">="
            elif "<=" in self.text: opcode = "<="
            elif "power" in self.text: opcode = "power"
            elif "not" in self.text: opcode = "not"
            elif "and" in self.text: opcode = "and"
            elif "or" in self.text: opcode = "or"
            else:
                opcode = "Get"
                
        return {
            "type": "expr",
            "opcode": opcode,
            "params": self.get_slot_values()
        }
    
    def get_slot_values(self):
        values = []
        for slot in self.slots:
            val = slot["value"]
            if isinstance(val, Block):  
                values.append(val.compile_expr())
            else:
                values.append(val)
        return values
    
    def to_dict(self):
        data = {
            "opcode": self.text.split('[')[0].strip(), 
            "params": self.get_slot_values(),          
            "next": None,                              
            "substack": None                           
        }

        if self.btype == "l" and self.nested_child:
            data["substack"] = self.nested_child.to_dict()

        if self.child:
            data["next"] = self.child.to_dict()

        return data