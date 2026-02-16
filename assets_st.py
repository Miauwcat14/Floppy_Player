import os
import pygame
from font import *

class AssetsStorage:
    def __init__(self, panel_rect=pygame.Rect(0, 0, 256, 256), mouse=None, on_close=None, on_load_request=None):
        self.rect = panel_rect.copy()
        self.font = Font("Fonts/power clear.ttf", 12)
        self.mouse = mouse
        self.confirm_delete = False

        self.on_close = on_close
        self.on_load_request = on_load_request

        self.tabs = ["Images", "Tab 2", "Tab 3"]
        self.active_tab = 0
        self._tab_rects = []
        self._build_tab_rects()

        self.close_btn_rect = pygame.Rect(self.rect.right - 22, self.rect.y + 2, 18, 18)
        self.load_btn_rect = pygame.Rect(self.rect.right - 50, self.rect.bottom - 22, 44, 18)

        self.entries = []  
        self.scroll_y = 0.0
        self.selected_index = None

        self.search_bar_rect = pygame.Rect(self.rect.x + 6, self.rect.y + 26, self.rect.w - 12, 18)
        self.search_text = ""
        self.search_active = False
        self.rename_index = None
        self.rename_text = ""

        # --- Layout Fixes ---
        self.cols = 3
        self.cell_padding = 6
        self.thumb_size = 56
        self.cell_w = self.thumb_size + 2 * self.cell_padding
        # Added more vertical space for the name (increased from 14 to 20)
        self.cell_h = self.thumb_size + 2 * self.cell_padding + 20 
        # Expanded grid area height to prevent name clipping at bottom
        self.grid_area = pygame.Rect(self.rect.x + 6, self.rect.y + 50, self.rect.w - 12, self.rect.h - 80)

        self.bg_color = (18, 18, 28)
        self.tab_active_color = (60, 120, 200)
        self.tab_inactive_color = (30, 60, 90)
        self.btn_color = (80, 80, 100)
        self.btn_hover_color = (120, 50, 50)
        self.load_btn_color = (100, 150, 100)

    # ---------------------------
    # Public API (Fixed Remove)
    # ---------------------------
    def remove(self, name):
        idx = next((i for i, e in enumerate(self.entries) if e['name'] == name), None)
        if idx is not None:
            del self.entries[idx]
            # Reset selection because the indices of everything else just changed
            self.selected_index = None 
            self.rename_index = None
            self._clamp_scroll()

    def add_image(self, path, name=None):
        if not os.path.exists(path): raise FileNotFoundError(path)
        surf = pygame.image.load(path).convert_alpha()
        base = os.path.splitext(os.path.basename(path))[0]
        final_name = self._ensure_unique_name(name or base)
        self._append_entry(final_name, surf)
        return final_name

    def add_surface(self, surface: pygame.Surface, name=None):
        name = self._ensure_unique_name(name or f"surf{len(self.entries)+1}")
        self._append_entry(name, surface)
        return name

    def set_name(self, old_name, new_name):
        idx = next((i for i, e in enumerate(self.entries) if e['name'] == old_name), None)
        if idx is not None:
            new_final = self._ensure_unique_name(new_name, skip_index=idx)
            self.entries[idx]['name'] = new_final
            return new_final
        return old_name

    # ---------------------------
    # Internal helpers
    # ---------------------------
    def _ensure_unique_name(self, name, skip_index=None):
        base = name
        names = [e['name'] for i, e in enumerate(self.entries) if i != skip_index]
        if name not in names: return name
        i = 1
        while f"{base}_{i}" in names: i += 1
        return f"{base}_{i}"

    def _append_entry(self, name, surf):
        sw, sh = surf.get_size()
        scale = min(self.thumb_size / max(sw, 1), self.thumb_size / max(sh, 1), 1.0)
        tw, th = max(1, int(sw * scale)), max(1, int(sh * scale))
        thumb_s = pygame.transform.smoothscale(surf, (tw, th))
        canvas = pygame.Surface((self.thumb_size, self.thumb_size), pygame.SRCALPHA)
        canvas.blit(thumb_s, ((self.thumb_size - tw) // 2, (self.thumb_size - th) // 2))
        self.entries.append({'name': name, 'surf': surf, 'thumb': canvas})

    def _build_tab_rects(self):
        self._tab_rects = []
        available_w = max(0, self.rect.w - 25)
        tab_w = max(40, available_w // len(self.tabs))
        for i in range(len(self.tabs)):
            self._tab_rects.append(pygame.Rect(self.rect.x + i * tab_w, self.rect.y, tab_w, 22))

    # ---------------------------
    # Event handling
    # ---------------------------
    def handle_event(self, event):
        def get_mpos():
            if self.mouse: return self.mouse.hitbox.center
            return pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.confirm_delete: return True
            mx, my = get_mpos()

            if self.close_btn_rect.collidepoint((mx, my)):
                if self.on_close: self.on_close()
                return True

            if self.active_tab == 0 and self.load_btn_rect.collidepoint((mx, my)):
                if self.on_load_request: self.on_load_request()
                return True

            for i, r in enumerate(self._tab_rects):
                if r.collidepoint((mx, my)):
                    self.active_tab, self.search_active, self.rename_index = i, False, None
                    return True

            if self.search_bar_rect.collidepoint((mx, my)):
                self.search_active = True
                return True
            else: self.search_active = False

            if self.active_tab == 0 and self.grid_area.collidepoint((mx, my)):
                rel_x, rel_y = mx - self.grid_area.x, my - self.grid_area.y + int(self.scroll_y)
                col, row = int(rel_x // self.cell_w), int(rel_y // self.cell_h)
                if 0 <= col < self.cols:
                    idx = row * self.cols + col
                    f_indices = self._filtered_indices()
                    if 0 <= idx < len(f_indices):
                        real_idx = f_indices[idx]
                        if self.selected_index == real_idx:
                            self.rename_index, self.rename_text = real_idx, self.entries[real_idx]['name']
                        else:
                            self.selected_index, self.rename_index = real_idx, None
                        return True

        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(get_mpos()):
                self.scroll_y -= event.y * 20
                self._clamp_scroll()
                return True

        if event.type == pygame.KEYDOWN:
            if self.confirm_delete:
                if event.key == pygame.K_RETURN:
                    if self.selected_index is not None:
                        self.remove(self.entries[self.selected_index]['name'])
                    self.confirm_delete = False
                elif event.key == pygame.K_ESCAPE: self.confirm_delete = False
                return True

            if self.rename_index is not None:
                if event.key == pygame.K_RETURN:
                    self.set_name(self.entries[self.rename_index]['name'], self.rename_text.strip())
                    self.rename_index = None
                elif event.key == pygame.K_ESCAPE: self.rename_index = None
                elif event.key == pygame.K_BACKSPACE: self.rename_text = self.rename_text[:-1]
                elif event.unicode.isprintable(): self.rename_text += event.unicode
                return True

            if not self.search_active and self.selected_index is not None:
                if event.key == pygame.K_r:
                    self.rename_index, self.rename_text = self.selected_index, self.entries[self.selected_index]['name']
                    return True
                if event.key == pygame.K_DELETE:
                    self.confirm_delete = True
                    return True

            if self.search_active:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE): self.search_active = False
                elif event.key == pygame.K_BACKSPACE: self.search_text = self.search_text[:-1]
                elif event.unicode.isprintable(): self.search_text += event.unicode
                self._clamp_scroll()
                return True
        return False

    # ---------------------------
    # Rendering
    # ---------------------------
    def render(self, target_surf):
        mpos = self.mouse.hitbox.center if self.mouse else pygame.mouse.get_pos()
        hovered_ui = False

        pygame.draw.rect(target_surf, self.bg_color, self.rect)

        for i, r in enumerate(self._tab_rects):
            pygame.draw.rect(target_surf, self.tab_active_color if i == self.active_tab else self.tab_inactive_color, r)
            self.font.render(target_surf, self.tabs[i], (255,255,255), 12, (r.centerx - self.font.font.size(self.tabs[i])[0]//2, r.y + 3))
            if r.collidepoint(mpos): hovered_ui = True

        x_col = self.btn_hover_color if self.close_btn_rect.collidepoint(mpos) else self.btn_color
        pygame.draw.rect(target_surf, x_col, self.close_btn_rect, border_radius=2)
        self.font.render(target_surf, "X", (255,255,255), 12, (self.close_btn_rect.x + 5, self.close_btn_rect.y + 2))
        if self.close_btn_rect.collidepoint(mpos): hovered_ui = True

        pygame.draw.rect(target_surf, (255,255,255), self.search_bar_rect, 1)
        self.font.render(target_surf, self.search_text + ("_" if self.search_active else ""), (255,255,255), 12, (self.search_bar_rect.x + 5, self.search_bar_rect.y + 2))
        if self.search_bar_rect.collidepoint(mpos): hovered_ui = True

        if self.active_tab == 0:
            h_container = [hovered_ui]
            self._render_tab_images(target_surf, mpos, h_container)
            hovered_ui = h_container[0]

            l_col = self.load_btn_color if self.load_btn_rect.collidepoint(mpos) else self.btn_color
            pygame.draw.rect(target_surf, l_col, self.load_btn_rect, border_radius=2)
            self.font.render(target_surf, "LOAD", (255,255,255), 10, (self.load_btn_rect.x + 6, self.load_btn_rect.y + 3))
            if self.load_btn_rect.collidepoint(mpos): hovered_ui = True

        if self.confirm_delete:
            overlay = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            target_surf.blit(overlay, self.rect.topleft)
            self.font.render(target_surf, "DELETE ASSET?", (255, 50, 50), 14, (self.rect.centerx - 45, self.rect.centery - 10))
            self.font.render(target_surf, "[Enter] Ok  [Esc] No", (200, 200, 200), 10, (self.rect.centerx - 55, self.rect.centery + 10))

        if self.mouse: self.mouse.set_state(1 if hovered_ui else 0)

    def _render_tab_images(self, surf, mpos, h_container):
        prev_clip = surf.get_clip()
        surf.set_clip(self.grid_area)

        filtered = self._filtered_entries()
        f_indices = self._filtered_indices()
        self._clamp_scroll()

        start_y = self.grid_area.y - int(self.scroll_y)
        hovered_any = False

        for idx, entry in enumerate(filtered):
            cx = self.grid_area.x + (idx % self.cols) * self.cell_w + self.cell_padding
            cy = start_y + (idx // self.cols) * self.cell_h + self.cell_padding
            cell_rect = pygame.Rect(cx - self.cell_padding, cy - self.cell_padding, self.cell_w, self.cell_h)
            
            pygame.draw.rect(surf, (40,40,60), cell_rect)
            surf.blit(entry['thumb'], (cx, cy))

            real_idx = f_indices[idx]
            nm = (self.rename_text + "_") if self.rename_index == real_idx else entry['name']
            if len(nm) > 14: nm = nm[:11] + "..."
            self.font.render(surf, nm, (220,220,220), 11, (cx, cy + self.thumb_size + 4))

            if self.selected_index == real_idx:
                pygame.draw.rect(surf, (200,200,60), cell_rect, 2)
            if cell_rect.collidepoint(mpos): hovered_any = True

        surf.set_clip(prev_clip)
        h_container[0] = h_container[0] or hovered_any

    def _filtered_entries(self):
        q = self.search_text.lower()
        return [e for e in self.entries if q in e['name'].lower()]

    def _filtered_indices(self):
        q = self.search_text.lower()
        return [i for i, e in enumerate(self.entries) if q in e['name'].lower()]

    def _clamp_scroll(self):
        content_h = ((len(self._filtered_entries()) + self.cols - 1) // self.cols) * self.cell_h
        max_scroll = max(0, content_h - self.grid_area.h)
        self.scroll_y = max(0.0, min(self.scroll_y, float(max_scroll)))

# Example usage
if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((512,512))
    storage = AssetsStorage(pygame.Rect(0, 0, 256, 256))
    try:
        storage.add_image("testing/cat_tex.png", "default")
    except Exception:
        pass

    running = True
    clock = pygame.time.Clock()
    while running:
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:
                running = False
            storage.handle_event(ev)

        screen.fill((30,30,40))
        storage.render(screen)
        pygame.display.flip()
        clock.tick(60)