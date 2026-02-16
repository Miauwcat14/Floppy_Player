import pygame

class Font:
    def __init__(self, file:str, size:int):
        pygame.font.init()
        self.font = pygame.font.Font(file, size)
        self.file = file
        self.size = size

    def render(self, screen, text:str, color, size:int, pos:tuple):
        if size != self.size:
            self.size = size
            self.font = pygame.font.Font(self.file, size)
        surf = self.font.render(text, True, color)
        screen.blit(surf, pos)