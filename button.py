import pygame

class Button:
    def __init__(self, rect, font_chars:list={
        "file":None, "text":"button", "size":12, "color":(0, 0, 0), "centered":True
    }):
        self.hitbox = pygame.Rect(rect[0], rect[1], rect[2], rect[3])
        self.clicked = False
        self.font_chars = font_chars
        self.font = None
        self.hover = False
        self.size = 1
        self.ori = (self.hitbox.width, self.hitbox.height)

    def update(self, mouse):
        action = False
        if self.hitbox.width < self.ori[0] * self.size: self.hitbox.width = self.ori[0] * self.size
        if self.hitbox.height < self.ori[1] * self.size: self.hitbox.height = self.ori[1] * self.size
        if self.hitbox.colliderect(mouse.hitbox):
            self.hover = True
            if pygame.mouse.get_pressed()[0]:
                if not self.clicked:
                    self.clicked = True
                    action = True
            else:
                self.clicked = False
        else:
            self.hover = False
        return action
    
    def render(self, screen, img=None, color=(100, 100, 100)):
        if self.font_chars["centered"]:
                pos = (self.hitbox.width // 4, self.hitbox.height // 4)
        else:
            pos = (self.hitbox.x, self.hitbox.y)
        if img is None:
            pygame.draw.rect(screen, color, self.hitbox, border_radius=2)
            pygame.draw.rect(screen, (0, 0, 0), self.hitbox, border_radius=2, width=2)
            self.font.render(screen, self.font_chars["text"], self.font_chars["color"], self.font_chars["size"], pos)
        else:
            img =pygame.transform.scale(img, (self.hitbox.width, self.hitbox.height))
            screen.blit(img, (self.hitbox.x, self.hitbox.y))