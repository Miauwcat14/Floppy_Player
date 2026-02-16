import pygame
import sys
import time
import random
from button import *
from font import *
from mouse import *
from reader import *

def main():
    pygame.init()
    #Display
    screen_size = pygame.display.Info()
    window_size = (screen_size.current_h, screen_size.current_h)
    screen = pygame.Surface((256, 256))
    display = pygame.display.set_mode((screen_size.current_w, screen_size.current_h) ,pygame.DOUBLEBUF | pygame.FULLSCREEN)

    #Program variables
    clock = pygame.time.Clock()
    FPS_CAP = 60
    run = True
    is_menu = True
    is_editor = False
    is_error = False
    is_transition = False
    slide = 1

    #variables init
    username = "Miauw"
    current_sel = "Minesweeper Ultra"
    sensitivity = 0.25

    #assets init
    quit_b = Button((8, 7, 70, 20))
    build_b = Button((185, 2, 32, 32))
    profile_b = Button((147, 2, 31, 31))
    config_b = Button((222, 2, 32, 32))
    home_b = Button((1, 1, 23, 23))

    font = Font("Fonts\power clear.ttf", 12)
    mouse = Mouse()
    quit = pygame.image.load("assets/quit.png").convert()
    quit_h = pygame.image.load("assets/quit_hover.png").convert()
    bg = pygame.image.load("assets/bg.png").convert()
    picdef = pygame.image.load("assets/userpicdefault.png").convert()
    picdef_h = pygame.image.load("assets/userpicdefault_h.png").convert()
    build = pygame.image.load("assets/build.png").convert()
    build_h = pygame.image.load("assets/build_h.png").convert()
    config = pygame.image.load("assets/config.png").convert()
    config_h = pygame.image.load("assets/config_h.png").convert()
    home = pygame.image.load("assets/home.png").convert()
    home_h = pygame.image.load("assets/home_h.png").convert()
    ed_bg = pygame.image.load("assets/editor_bg.png").convert()
    slide1 = pygame.image.load("assets/slide1.png").convert()
    slide2 = pygame.image.load("assets/slide2.png").convert()

    def transition(timey):
        screen.blit(slide1, (0, 0))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(timey/4)
        screen.blit(slide2, (0, 0))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(timey/4)
        screen.fill((0, 0, 0))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(2)
        screen.blit(slide2, (0, 0))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(timey/4)
        screen.blit(slide1, (0, 0))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(timey/4)
        return "done"

    def load_info(game:str):
        try:
            info = read_file(f"Disks/{game}/info.json")
            thumbnail = pygame.image.load(f"Disks/{game}/assets/sprites/thumbnail.png").convert()
            #thumbnail_big = pygame.transform
            return [info, thumbnail]
        except:
            return "Could not load game :("
        
    def b_hover(bt, norm, hover):
        if bt.hover:
            bt.render(screen, norm)
            mouse.set_state(1)
        else:
            bt.render(screen, hover)
        
    #game init
    game = load_info(current_sel)
    if game == "Could not load game :(":
        is_error = True

    for _ in range(random.randint(1, 5)):
        screen.fill((0, 0, 0))
        font.render(screen, "Booting console.", (255, 255, 255), 12, (159, 242))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(1)
        screen.fill((0, 0, 0))
        font.render(screen, "Booting console..", (255, 255, 255), 12, (159, 242))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(1)
        screen.fill((0, 0, 0))
        font.render(screen, "Booting console...", (255, 255, 255), 12, (159, 242))
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        time.sleep(1)
    time.sleep(2)
    screen.fill((0, 0, 0))
    sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
    display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
    pygame.display.flip()
    time.sleep(2)
    screen.blit(slide2, (0, 0))
    sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
    display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
    pygame.display.flip()
    time.sleep(0.075)
    screen.blit(slide1, (0, 0))
    sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
    display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
    pygame.display.flip()
    time.sleep(0.075)
    pygame.mouse.set_pos((128, 128))

    clock.tick(FPS_CAP)

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            run = False
            
        screen.fill((255, 255, 255))

        mouse.set_state(0)

        if is_menu:
            if not is_error:
                screen.blit(bg, (0, 0))
                #update buttons
                if quit_b.update(mouse):
                    run = False
                build_b.update(mouse)
                profile_b.update(mouse)
                config_b.update(mouse)

                b_hover(quit_b, quit_h, quit)
                b_hover(build_b, build_h, build)
                b_hover(profile_b, picdef_h, picdef)
                b_hover(config_b, config_h, config)

                #update blit
                screen.blit(game[1], (35, 67))
                font.render(screen, f"{username}", (0, 0, 0), 24, (95, 8))
                font.render(screen, game[0]["name"], (0, 0, 0), 12, (22, 52))
                font.render(screen, f"Made by: {game[0]["createdby"]}", (255, 255, 255), 12, (5, 204))
                font.render(screen, f"Date Created: {game[0]["date"]}", (255, 255, 255), 12, (5, 222))
                font.render(screen, f"{game[0]["desc"]}", (255, 255, 255), 12, (152, 204))
            else:
                font.render(screen, "Could not load games :(", (255, 255, 255), 24, (30, 188))

        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > 255 / sensitivity:
            pygame.mouse.set_pos((255 / sensitivity, mouse_pos[1]))
        if mouse_pos[1] > 255 / sensitivity:
            pygame.mouse.set_pos((mouse_pos[0], 255 / sensitivity))
        mouse.render(screen, sensitivity)

        if is_transition:
            slide = transition(1)
            if slide == "done":
                is_transition = False
                slide = 1
        
        #Screen Update
        sc = pygame.transform.scale(screen, (window_size[0], window_size[1]))
        display.blit(sc, ((screen_size.current_w - window_size[0]) // 2, 0))
        pygame.display.flip()
        clock.tick(FPS_CAP)
        pygame.display.set_caption(f"Floppy Player - FPS: {clock.get_fps()}")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()