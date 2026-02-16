import pygame
class Mouse:
    def __init__(self, images={"normal":"assets/mouse.png","hover":"assets/mouse_hover.png"},states=["normal","hover"]):
        pygame.mouse.set_visible(False)
        self.image,self.state,self.states,self.hitbox=self.load_images(images),states[0],states,pygame.Rect(0,0,1,1)
    def set_state(self,num:int):
        try:self.state=self.states[num]
        except:self.state=self.states[0]
    def render(self,screen,sens:int=1):
        self.hitbox.x,self.hitbox.y=pygame.mouse.get_pos()[0]*sens,pygame.mouse.get_pos()[1]*sens
        screen.blit(self.image[self.state],(pygame.mouse.get_pos()[0]*sens,pygame.mouse.get_pos()[1]*sens))
    def load_images(self,images:dict):
        states,idx=[],-1
        for st in images:states.append(st)
        for index in images.values():
            img=pygame.image.load(index).convert_alpha()
            idx+=1
            images[states[idx]]=img
        return images