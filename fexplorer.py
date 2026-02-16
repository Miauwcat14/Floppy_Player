import pygame
import os
import string
from font import *

class FileExplorer:
    def __init__(self, font_path="Fonts/power clear.ttf"):
        self.font = Font(font_path, 12)
        self.current_path = os.getcwd()
        
        # State
        self.all_entries = []
        self.filtered_entries = []
        self.drives = self.get_drives()
        
        self.scroll_y = 0
        self.selected_file = None
        self.search_query = ""
        self.is_searching = False
        
        # UI Rects
        self.search_bar_rect = pygame.Rect(5, 25, 246, 15)
        self.list_clip = pygame.Rect(0, 42, 256, 180) # Shortened to make room for buttons
        self.btn_cancel = pygame.Rect(140, 230, 50, 20)
        self.btn_ok = pygame.Rect(195, 230, 50, 20)
        
        self.load_directory(self.current_path)

    def get_drives(self):
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
        return drives

    def load_directory(self, path):
        try:
            items = os.listdir(path)
            self.current_path = path
            self.all_entries = [{"name": "..", "type": "folder"}]
            for d in self.drives:
                self.all_entries.append({"name": d, "type": "drive"})
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    self.all_entries.append({"name": item, "type": "folder"})
                elif item.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    self.all_entries.append({"name": item, "type": "image"})
            self.filtered_entries = self.all_entries[:]
            self.scroll_y = 0
        except Exception: pass

    def update(self, events, mouse):
        # Handle Typing
        if self.is_searching:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        self.search_query = self.search_query[:-1]
                    elif event.key == pygame.K_RETURN:
                        self.is_searching = False
                    else:
                        if len(self.search_query) < 20:
                            self.search_query += event.unicode

        if self.search_query:
            self.filtered_entries = [e for e in self.all_entries if self.search_query.lower() in e["name"].lower()]
        else:
            self.filtered_entries = self.all_entries

        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                self.scroll_y = min(0, self.scroll_y + event.y * 15)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # OK / Cancel detection
                if mouse.hitbox.colliderect(self.btn_cancel):
                    return "cancel"
                if mouse.hitbox.colliderect(self.btn_ok):
                    return "ok"

                self.is_searching = mouse.hitbox.colliderect(self.search_bar_rect)
                
                for i, entry in enumerate(self.filtered_entries):
                    y_pos = 45 + (i * 18) + self.scroll_y
                    entry_rect = pygame.Rect(5, y_pos, 240, 16)
                    if mouse.hitbox.colliderect(entry_rect) and self.list_clip.collidepoint(mouse.hitbox.topleft):
                        if entry["type"] in ["folder", "drive"]:
                            target = entry["name"] if entry["type"] == "drive" else os.path.join(self.current_path, entry["name"])
                            self.load_directory(os.path.abspath(target))
                            self.search_query = ""
                            break
                        elif entry["type"] == "image":
                            self.selected_file = os.path.join(self.current_path, entry["name"])
        return None

    def draw(self, screen, mouse):
        # Background
        pygame.draw.rect(screen, (25, 25, 30), (0, 0, 256, 256))
        
        # Header
        pygame.draw.rect(screen, (40, 40, 55), (0, 0, 256, 22))
        path_text = self.current_path[-35:] if len(self.current_path) > 35 else self.current_path
        self.font.render(screen, path_text, (180, 180, 180), 12, (5, 4))

        # Search Bar
        sb_col = (70, 70, 100) if self.is_searching else (40, 40, 60)
        pygame.draw.rect(screen, sb_col, self.search_bar_rect, border_radius=3)
        self.font.render(screen, self.search_query or "Search...", (255, 255, 255), 12, (10, 27))

        # List Area
        prev_clip = screen.get_clip()
        screen.set_clip(self.list_clip)
        for i, entry in enumerate(self.filtered_entries):
            y_pos = 45 + (i * 18) + self.scroll_y
            entry_rect = pygame.Rect(5, y_pos, 246, 16)
            if mouse.hitbox.colliderect(entry_rect):
                pygame.draw.rect(screen, (50, 50, 75), entry_rect, border_radius=2)
                mouse.set_state(1)
            
            col = (100, 200, 255) if entry["type"] in ["folder", "drive"] else (150, 255, 150)
            # Highlight selected file
            if self.selected_file and os.path.basename(self.selected_file) == entry["name"]:
                pygame.draw.rect(screen, (100, 100, 0), entry_rect, 1)

            self.font.render(screen, entry["name"][:35], col, 12, (10, y_pos + 2))
        screen.set_clip(prev_clip)

        # Bottom Bar & Buttons
        pygame.draw.rect(screen, (30, 30, 40), (0, 225, 256, 31))
        
        # Draw Cancel
        c_col = (80, 40, 40) if mouse.hitbox.colliderect(self.btn_cancel) else (60, 30, 30)
        pygame.draw.rect(screen, c_col, self.btn_cancel, border_radius=3)
        self.font.render(screen, "CANCEL", (255, 255, 255), 12, (self.btn_cancel.x+5, self.btn_cancel.y+3))
        
        # Draw OK
        ok_col = (40, 80, 40) if mouse.hitbox.colliderect(self.btn_ok) else (30, 60, 30)
        pygame.draw.rect(screen, ok_col, self.btn_ok, border_radius=3)
        self.font.render(screen, "OK", (255, 255, 255), 12, (self.btn_ok.x+15, self.btn_ok.y+3))

        if self.selected_file:
            self.font.render(screen, os.path.basename(self.selected_file)[:20], (255, 255, 255), 12, (5, 232))