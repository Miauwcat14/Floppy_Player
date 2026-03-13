import pygame
import sys
import os
import copy

# Try to import scrap for clipboard
try:
    import pygame.scrap
    SCRAP_SUPPORT = True
except:
    SCRAP_SUPPORT = False

from font import Font
from mouse import Mouse
from button import Button

# --- CONFIG ---
WORKSPACE_DIR = "workspace"
if not os.path.exists(WORKSPACE_DIR):
    os.makedirs(WORKSPACE_DIR)

def main():
    pygame.init()
    
    # --- 1. DISPLAY SETUP ---
    INT_W, INT_H = 455, 256
    screen = pygame.Surface((INT_W, INT_H))
    
    info = pygame.display.Info()
    monitor_w, monitor_h = info.current_w, info.current_h
    scale = min(monitor_w / INT_W, monitor_h / INT_H)
    sw, sh = int(INT_W * scale), int(INT_H * scale)
    ox, oy = (monitor_w - sw) // 2, (monitor_h - sh) // 2
    
    display = pygame.display.set_mode((monitor_w, monitor_h), pygame.DOUBLEBUF | pygame.FULLSCREEN)

    if SCRAP_SUPPORT:
        try:
            pygame.scrap.init()
            pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)
        except: pass

    # --- PROGRAM VARIABLES ---
    clock = pygame.time.Clock()
    run = True
    sensitivity = 0.25
    pygame.key.set_repeat(300, 30)
    
    TOP_BAR_H = 22        
    LINE_SPACING = 4      
    TEXT_X_MARGIN = 6     
    
    custom_font = Font(r"Fonts\power clear.ttf", 12)
    font_size = 12
    base_h = custom_font.get_size("A", font_size)[1]
    total_line_h = base_h + LINE_SPACING
    
    mouse = Mouse()
    save_b = Button((375, 4, 34, 14), {"text":"SAVE", "size":10, "color":(255,255,255), "centered":True})
    load_b = Button((415, 4, 34, 14), {"text":"LOAD", "size":10, "color":(255,255,255), "centered":True})
    save_b.font = load_b.font = custom_font

    # --- STATE HELPERS ---
    def new_tab(name="untitled"):
        return {
            "name": name, "text_lines": [""], "line_cache": [[0]],
            "cursor_row": 0, "cursor_col": 0, "scroll_y": 0,
            "undo_stack": [], "redo_stack": [], "select_anchor": None
        }

    def save_state(tab):
        """Pushes current text and cursor to undo stack."""
        state = {
            "lines": list(tab["text_lines"]),
            "row": tab["cursor_row"],
            "col": tab["cursor_col"]
        }
        tab["undo_stack"].append(state)
        if len(tab["undo_stack"]) > 50: tab["undo_stack"].pop(0)
        tab["redo_stack"] = [] # Clear redo on new action

    def update_cache(row, tab):
        line = tab["text_lines"][row]
        w = [0]
        cur_x = 0
        for c in line:
            cur_x += custom_font.get_size(c, font_size)[0]
            w.append(cur_x)
        if row < len(tab["line_cache"]): tab["line_cache"][row] = w
        else: tab["line_cache"].append(w)

    def full_rebuild(tab):
        tab["line_cache"] = []
        for i in range(len(tab["text_lines"])): update_cache(i, tab)

    def get_sel_range(tab):
        if not tab["select_anchor"]: return None
        p1, p2 = tab["select_anchor"], (tab["cursor_row"], tab["cursor_col"])
        return (p1, p2) if (p1[0] < p2[0] or (p1[0] == p2[0] and p1[1] < p2[1])) else (p2, p1)

    def delete_sel(tab):
        if not tab["select_anchor"]: return False
        save_state(tab)
        s, e = get_sel_range(tab)
        tab["text_lines"][s[0]] = tab["text_lines"][s[0]][:s[1]] + tab["text_lines"][e[0]][e[1]:]
        del tab["text_lines"][s[0]+1 : e[0]+1]
        del tab["line_cache"][s[0]+1 : e[0]+1]
        tab["cursor_row"], tab["cursor_col"] = s[0], s[1]
        tab["select_anchor"] = None
        update_cache(tab["cursor_row"], tab)
        return True

    def find_word_boundary(line, col, direction):
        if direction == -1: # Left
            if col <= 0: return 0
            idx = col - 1
            while idx > 0 and line[idx-1] == " ": idx -= 1
            while idx > 0 and line[idx-1] != " ": idx -= 1
            return idx
        else: # Right
            if col >= len(line): return len(line)
            idx = col + 1
            while idx < len(line) and line[idx] == " ": idx += 1
            while idx < len(line) and line[idx] != " ": idx += 1
            return idx

    tabs = [new_tab()]
    active_tab = 0
    file_dialog = {"active": False, "mode": None, "files": [], "input_name": "", "selected_index": 0}
    cursor_visible, cursor_timer = True, 0
    is_dragging = False

    while run:
        dt = clock.tick(60)
        cursor_timer += dt
        if cursor_timer >= 500: cursor_visible, cursor_timer = not cursor_visible, 0
        
        mx, my = pygame.mouse.get_pos()
        ix, iy = mx * sensitivity, my * sensitivity
        mouse.hitbox.x, mouse.hitbox.y = ix, iy
        curr = tabs[active_tab]
        max_scroll = max(0, (len(curr["text_lines"]) * total_line_h) - (INT_H - TOP_BAR_H))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: run = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if save_b.update(mouse):
                        file_dialog.update({"active": True, "mode": "save", "input_name": ""})
                        file_dialog["files"] = [f for f in os.listdir(WORKSPACE_DIR) if f.endswith(".txt")]
                    elif load_b.update(mouse):
                        file_dialog.update({"active": True, "mode": "load", "selected_index": 0})
                        file_dialog["files"] = [f for f in os.listdir(WORKSPACE_DIR) if f.endswith(".txt")]
                    elif iy < TOP_BAR_H:
                        tx = 5
                        for i in range(len(tabs)):
                            if tx < ix < tx + 60: active_tab = i; break
                            tx += 65
                    elif not file_dialog["active"]:
                        adj_y = iy - TOP_BAR_H + curr["scroll_y"]
                        curr["cursor_row"] = max(0, min(int(adj_y // total_line_h), len(curr["text_lines"]) - 1))
                        ws = curr["line_cache"][curr["cursor_row"]]
                        best = 0; diff = 999
                        for col, x in enumerate(ws):
                            d = abs((ix - TEXT_X_MARGIN) - x)
                            if d < diff: diff, best = d, col
                        curr["cursor_col"] = best
                        curr["select_anchor"] = (curr["cursor_row"], curr["cursor_col"])
                        is_dragging = True
                elif event.button == 4: curr["scroll_y"] = max(0, curr["scroll_y"] - 20)
                elif event.button == 5: curr["scroll_y"] = min(max_scroll, curr["scroll_y"] + 20)

            elif event.type == pygame.MOUSEBUTTONUP: is_dragging = False
            elif event.type == pygame.MOUSEMOTION and is_dragging:
                adj_y = iy - TOP_BAR_H + curr["scroll_y"]
                curr["cursor_row"] = max(0, min(int(adj_y // total_line_h), len(curr["text_lines"]) - 1))
                ws = curr["line_cache"][curr["cursor_row"]]
                best = 0; diff = 999
                for col, x in enumerate(ws):
                    d = abs((ix - TEXT_X_MARGIN) - x)
                    if d < diff: diff, best = d, col
                curr["cursor_col"] = best

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl = mods & pygame.KMOD_CTRL
                shift = mods & pygame.KMOD_SHIFT
                
                if file_dialog["active"]:
                    if event.key == pygame.K_ESCAPE: file_dialog["active"] = False
                    elif file_dialog["mode"] == "save":
                        if event.key == pygame.K_RETURN and file_dialog["input_name"]:
                            with open(os.path.join(WORKSPACE_DIR, file_dialog["input_name"] + ".txt"), "w") as f:
                                f.write("\n".join(curr["text_lines"]))
                            curr["name"] = file_dialog["input_name"]; file_dialog["active"] = False
                        elif event.key == pygame.K_BACKSPACE: file_dialog["input_name"] = file_dialog["input_name"][:-1]
                    elif file_dialog["mode"] == "load":
                        if event.key == pygame.K_RETURN and file_dialog["files"]:
                            fn = file_dialog["files"][file_dialog["selected_index"]]
                            with open(os.path.join(WORKSPACE_DIR, fn), "r") as f:
                                nt = new_tab(fn); nt["text_lines"] = f.read().splitlines() or [""]
                                full_rebuild(nt); tabs.append(nt); active_tab = len(tabs)-1
                            file_dialog["active"] = False
                        elif event.key == pygame.K_UP: file_dialog["selected_index"] = max(0, file_dialog["selected_index"] - 1)
                        elif event.key == pygame.K_DOWN: file_dialog["selected_index"] = min(len(file_dialog["files"])-1, file_dialog["selected_index"]+1)
                    continue

                if event.key == pygame.K_ESCAPE: run = False

                # --- ARROW KEYS & SELECTION ---
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    if shift and curr["select_anchor"] is None:
                        curr["select_anchor"] = (curr["cursor_row"], curr["cursor_col"])
                    elif not shift:
                        curr["select_anchor"] = None

                    if event.key == pygame.K_LEFT:
                        if ctrl: curr["cursor_col"] = find_word_boundary(curr["text_lines"][curr["cursor_row"]], curr["cursor_col"], -1)
                        elif curr["cursor_col"] > 0: curr["cursor_col"] -= 1
                        elif curr["cursor_row"] > 0:
                            curr["cursor_row"] -= 1
                            curr["cursor_col"] = len(curr["text_lines"][curr["cursor_row"]])
                    elif event.key == pygame.K_RIGHT:
                        if ctrl: curr["cursor_col"] = find_word_boundary(curr["text_lines"][curr["cursor_row"]], curr["cursor_col"], 1)
                        elif curr["cursor_col"] < len(curr["text_lines"][curr["cursor_row"]]): curr["cursor_col"] += 1
                        elif curr["cursor_row"] < len(curr["text_lines"]) - 1:
                            curr["cursor_row"] += 1; curr["cursor_col"] = 0
                    elif event.key == pygame.K_UP:
                        if curr["cursor_row"] > 0:
                            curr["cursor_row"] -= 1
                            curr["cursor_col"] = min(curr["cursor_col"], len(curr["text_lines"][curr["cursor_row"]]))
                    elif event.key == pygame.K_DOWN:
                        if curr["cursor_row"] < len(curr["text_lines"]) - 1:
                            curr["cursor_row"] += 1
                            curr["cursor_col"] = min(curr["cursor_col"], len(curr["text_lines"][curr["cursor_row"]]))
                    
                    # Ensure cursor is visible after move
                    cur_y = TOP_BAR_H + (curr["cursor_row"] * total_line_h)
                    if cur_y - curr["scroll_y"] < TOP_BAR_H: curr["scroll_y"] = cur_y - TOP_BAR_H
                    elif cur_y - curr["scroll_y"] > INT_H - total_line_h: curr["scroll_y"] = cur_y - INT_H + total_line_h

                # --- UNDO / REDO ---
                elif ctrl and event.key == pygame.K_z:
                    if curr["undo_stack"]:
                        # Save current state to redo stack
                        curr["redo_stack"].append({"lines": list(curr["text_lines"]), "row": curr["cursor_row"], "col": curr["cursor_col"]})
                        state = curr["undo_stack"].pop()
                        curr["text_lines"], curr["cursor_row"], curr["cursor_col"] = state["lines"], state["row"], state["col"]
                        full_rebuild(curr)
                elif ctrl and event.key == pygame.K_y:
                    if curr["redo_stack"]:
                        curr["undo_stack"].append({"lines": list(curr["text_lines"]), "row": curr["cursor_row"], "col": curr["cursor_col"]})
                        state = curr["redo_stack"].pop()
                        curr["text_lines"], curr["cursor_row"], curr["cursor_col"] = state["lines"], state["row"], state["col"]
                        full_rebuild(curr)

                # --- CLIPBOARD / TABS / EDIT ---
                elif ctrl and event.key == pygame.K_c and curr["select_anchor"]:
                    s, e = get_sel_range(curr)
                    if s[0] == e[0]: txt = curr["text_lines"][s[0]][s[1]:e[1]]
                    else:
                        txt = curr["text_lines"][s[0]][s[1]:] + "\n"
                        for r in range(s[0]+1, e[0]): txt += curr["text_lines"][r] + "\n"
                        txt += curr["text_lines"][e[0]][:e[1]]
                    pygame.scrap.put(pygame.SCRAP_TEXT, txt.encode())

                elif ctrl and event.key == pygame.K_v:
                    raw = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if raw:
                        delete_sel(curr); save_state(curr)
                        clip = raw.decode().replace('\r', '').split('\n')
                        after = curr["text_lines"][curr["cursor_row"]][curr["cursor_col"]:]
                        curr["text_lines"][curr["cursor_row"]] = curr["text_lines"][curr["cursor_row"]][:curr["cursor_col"]] + clip[0]
                        for i in range(1, len(clip)):
                            curr["text_lines"].insert(curr["cursor_row"] + i, clip[i])
                        curr["cursor_row"] += len(clip) - 1
                        curr["cursor_col"] = len(clip[-1])
                        curr["text_lines"][curr["cursor_row"]] += after
                        full_rebuild(curr)

                elif ctrl and event.key == pygame.K_t: tabs.append(new_tab()); active_tab = len(tabs)-1
                elif ctrl and event.key == pygame.K_w and len(tabs)>1: tabs.pop(active_tab); active_tab = max(0, active_tab-1)
                
                elif event.key == pygame.K_BACKSPACE:
                    if not delete_sel(curr):
                        if curr["cursor_col"] > 0:
                            save_state(curr)
                            ln = curr["text_lines"][curr["cursor_row"]]
                            curr["text_lines"][curr["cursor_row"]] = ln[:curr["cursor_col"]-1] + ln[curr["cursor_col"]:]
                            curr["cursor_col"] -= 1; update_cache(curr["cursor_row"], curr)
                        elif curr["cursor_row"] > 0:
                            save_state(curr)
                            curr["cursor_col"] = len(curr["text_lines"][curr["cursor_row"]-1])
                            curr["text_lines"][curr["cursor_row"]-1] += curr["text_lines"][curr["cursor_row"]]
                            del curr["text_lines"][curr["cursor_row"]], curr["line_cache"][curr["cursor_row"]]
                            curr["cursor_row"] -= 1; update_cache(curr["cursor_row"], curr)
                elif event.key == pygame.K_RETURN:
                    delete_sel(curr); save_state(curr)
                    ln = curr["text_lines"][curr["cursor_row"]]
                    curr["text_lines"][curr["cursor_row"]] = ln[:curr["cursor_col"]]
                    curr["text_lines"].insert(curr["cursor_row"]+1, ln[curr["cursor_col"]:])
                    curr["line_cache"].insert(curr["cursor_row"]+1, [0])
                    update_cache(curr["cursor_row"], curr); update_cache(curr["cursor_row"]+1, curr)
                    curr["cursor_row"] += 1; curr["cursor_col"] = 0

            elif event.type == pygame.TEXTINPUT and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                if file_dialog["active"] and file_dialog["mode"] == "save": file_dialog["input_name"] += event.text
                elif not file_dialog["active"]:
                    delete_sel(curr); save_state(curr); ln = curr["text_lines"][curr["cursor_row"]]
                    curr["text_lines"][curr["cursor_row"]] = ln[:curr["cursor_col"]] + event.text + ln[curr["cursor_col"]:]
                    curr["cursor_col"] += len(event.text); update_cache(curr["cursor_row"], curr)

        # DRAW
        screen.fill((30, 30, 30))
        if curr["select_anchor"]:
            s, e = get_sel_range(curr)
            for r in range(s[0], e[0] + 1):
                sx = curr["line_cache"][r][s[1]] if r == s[0] else 0
                ex = curr["line_cache"][r][e[1]] if r == e[0] else curr["line_cache"][r][-1] + 4
                ry = TOP_BAR_H + (r * total_line_h) - curr["scroll_y"]
                if TOP_BAR_H - total_line_h < ry < INT_H:
                    pygame.draw.rect(screen, (0, 100, 200), (TEXT_X_MARGIN + sx, ry, max(ex - sx, 2), total_line_h))

        for i, ln in enumerate(curr["text_lines"]):
            dy = TOP_BAR_H + (i * total_line_h) - curr["scroll_y"]
            if TOP_BAR_H - total_line_h < dy < INT_H:
                custom_font.render(screen, ln, (220, 220, 220), font_size, (TEXT_X_MARGIN, dy))
                if i == curr["cursor_row"] and cursor_visible:
                    cx = TEXT_X_MARGIN + curr["line_cache"][i][curr["cursor_col"]]
                    pygame.draw.line(screen, (255, 255, 255), (cx, dy), (cx, dy + total_line_h - LINE_SPACING))

        # --- SCROLLBAR ---
        if max_scroll > 0:
            bar_h = INT_H - TOP_BAR_H
            thumb_h = max(20, (bar_h / (len(curr["text_lines"]) * total_line_h)) * bar_h)
            thumb_y = TOP_BAR_H + (curr["scroll_y"] / max_scroll) * (bar_h - thumb_h)
            pygame.draw.rect(screen, (50, 50, 50), (INT_W - 6, TOP_BAR_H, 6, bar_h))
            pygame.draw.rect(screen, (100, 100, 100), (INT_W - 5, thumb_y, 4, thumb_h), border_radius=2)

        # UI
        pygame.draw.rect(screen, (45, 45, 48), (0, 0, INT_W, TOP_BAR_H))
        tx = 5
        for i, t in enumerate(tabs):
            tab_c = (70, 70, 75) if i == active_tab else (40, 40, 40)
            pygame.draw.rect(screen, tab_c, (tx, 4, 60, 15))
            tw, _ = custom_font.get_size(t["name"][:8], 10)
            custom_font.render(screen, t["name"][:8], (255, 255, 255), 10, (tx + (30 - tw//2), 6))
            tx += 65

        save_b.render(screen, color=(60, 60, 60)); load_b.render(screen, color=(60, 60, 60))
        for b in [save_b, load_b]:
            tw, th = custom_font.get_size(b.font_chars["text"], 10)
            custom_font.render(screen, b.font_chars["text"], (255,255,255), 10, (b.hitbox.centerx - tw//2, b.hitbox.centery - th//2))

        if file_dialog["active"]:
            ov = pygame.Surface((INT_W, INT_H), pygame.SRCALPHA); ov.fill((0, 0, 0, 180)); screen.blit(ov, (0,0))
            pygame.draw.rect(screen, (40, 40, 45), (100, 40, 255, 150))
            if file_dialog["mode"] == "save":
                custom_font.render(screen, "SAVE AS:", (255, 255, 255), 12, (110, 50))
                custom_font.render(screen, file_dialog["input_name"] + "|", (255, 255, 0), 12, (110, 80))
            else:
                custom_font.render(screen, "LOAD FILE:", (255, 255, 255), 12, (110, 50))
                for idx, f in enumerate(file_dialog["files"][:8]):
                    c = (255, 255, 0) if idx == file_dialog["selected_index"] else (200, 200, 200)
                    custom_font.render(screen, f, c, 12, (110, 70 + idx*15))

        mouse.set_state(1 if (save_b.hover or load_b.hover) else 0)
        mouse.render(screen, sensitivity)
        display.blit(pygame.transform.scale(screen, (sw, sh)), (ox, oy))
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()