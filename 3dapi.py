import pygame
import numpy as np
from numba import njit, prange
import sys
import os
import math

# --- Optimized Rasterizer ---
@njit(fastmath=True, cache=True)
def draw_textured_triangle(px_array, z_buffer, v1, v2, v3, t1, t2, t3, texture, tex_alpha, sw, sh, intensity):
    min_x = int(max(0, math.floor(min(v1[0], v2[0], v3[0]))))
    max_x = int(min(sw - 1, math.ceil(max(v1[0], v2[0], v3[0]))))
    min_y = int(max(0, math.floor(min(v1[1], v2[1], v3[1]))))
    max_y = int(min(sh - 1, math.ceil(max(v1[1], v2[1], v3[1]))))

    den = (v2[1] - v3[1]) * (v1[0] - v3[0]) + (v3[0] - v2[0]) * (v1[1] - v3[1])
    if den == 0.0: return
    inv_den = 1.0 / den

    a1, b1 = (v2[1] - v3[1]) * inv_den, (v3[0] - v2[0]) * inv_den
    c1 = ((v2[1] - v3[1]) * (-v3[0]) + (v3[0] - v2[0]) * (-v3[1])) * inv_den
    a2, b2 = (v3[1] - v1[1]) * inv_den, (v1[0] - v3[0]) * inv_den
    c2 = ((v3[1] - v1[1]) * (-v3[0]) + (v1[0] - v3[0]) * (-v3[1])) * inv_den

    tw, th = texture.shape[0] - 1, texture.shape[1] - 1

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            w1 = a1 * x + b1 * y + c1
            w2 = a2 * x + b2 * y + c2
            w3 = 1.0 - w1 - w2
            if w1 >= 0.0 and w2 >= 0.0 and w3 >= 0.0:
                iz = w1 * v1[2] + w2 * v2[2] + w3 * v3[2]
                if iz > z_buffer[x, y]:
                    tx, ty = int((w1 * t1[0] + w2 * t2[0] + w3 * t3[0]) * tw), int((w1 * t1[1] + w2 * t2[1] + w3 * t3[1]) * th)
                    tx, ty = tx % (tw + 1), ty % (th + 1)
                    if tex_alpha[tx, ty] > 128:
                        z_buffer[x, y] = iz
                        px_array[x, y, 0] = np.uint8(texture[tx, ty, 0] * min(1.0, intensity))
                        px_array[x, y, 1] = np.uint8(texture[tx, ty, 1] * min(1.0, intensity))
                        px_array[x, y, 2] = np.uint8(texture[tx, ty, 2] * min(1.0, intensity))

@njit(parallel=True, fastmath=True, cache=True)
def render_submesh_numba(px_array, z_buffer, v_arr, v_world, faces, face_uvs, texture, tex_alpha, sw, sh, cull, lights, is_light):
    for i in prange(faces.shape[0]):
        p1w, p2w, p3w = v_world[faces[i,0]], v_world[faces[i,1]], v_world[faces[i,2]]
        normal = np.cross(p2w - p1w, p3w - p1w)
        n_len = np.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
        if n_len == 0: continue
        normal /= n_len

        if is_light:
            intensity = 1.0
        else:
            face_center = (p1w + p2w + p3w) / 3.0
            intensity = 0.15 
            for j in range(lights.shape[0]):
                l_dir = lights[j] - face_center
                l_dist_sq = l_dir[0]**2 + l_dir[1]**2 + l_dir[2]**2
                l_dist = np.sqrt(l_dist_sq)
                if l_dist != 0:
                    l_dir /= l_dist
                    dot = normal[0]*l_dir[0] + normal[1]*l_dir[1] + normal[2]*l_dir[2]
                    intensity += max(0.0, dot) * (1.0 / (1.0 + 0.01 * l_dist + 0.002 * l_dist_sq))

        v1, v2, v3 = v_arr[faces[i,0]], v_arr[faces[i,1]], v_arr[faces[i,2]]
        # Flipped the cross product check for culling to match coordinate flip
        if cull and not is_light:
            if (v2[0]-v1[0])*(v3[1]-v1[1]) - (v2[1]-v1[1])*(v3[0]-v1[0]) >= 0: continue

        draw_textured_triangle(px_array, z_buffer, v1, v2, v3, face_uvs[i,0], face_uvs[i,1], face_uvs[i,2], 
                               texture, tex_alpha, sw, sh, intensity)

class Engine3D:
    def __init__(self, obj_path=None):
        self.vertices = np.empty((0,3), dtype=np.float64)
        self.submeshes = [] # List of {'faces': arr, 'uvs': arr, 'tex': arr, 'alpha': arr}
        self.pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.rot = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.scale = np.array([1.0, 1.0, 1.0], dtype=np.float64)
        self.is_light = False 
        
        if obj_path: self.load_obj(obj_path)

    def load_obj(self, path):
        if not os.path.exists(path): return
        v_l, vt_l = [], []
        current_faces, current_uvs = [], []
        
        with open(path, 'r') as f:
            for line in f:
                s = line.split()
                if not s: continue
                if s[0] == 'v': v_l.append([float(x) for x in s[1:4]])
                elif s[0] == 'vt': vt_l.append([float(x) for x in s[1:3]])
                elif s[0] in ('usemtl', 'o', 'g'):
                    # Save existing submesh before starting new one
                    if current_faces:
                        self.add_submesh(current_faces, current_uvs)
                        current_faces, current_uvs = [], []
                elif s[0] == 'f':
                    idx = [p.split('/') for p in s[1:]]
                    for i in range(1, len(idx) - 1):
                        current_faces.append([int(idx[0][0])-1, int(idx[i][0])-1, int(idx[i+1][0])-1])
                        for k in [0, i, i+1]:
                            if len(idx[k]) > 1 and idx[k][1]:
                                uv = vt_l[int(idx[k][1])-1]
                                current_uvs.append([uv[0], 1.0 - uv[1]])
                            else: current_uvs.append([0.0, 0.0])
        
        if current_faces: self.add_submesh(current_faces, current_uvs)
        self.vertices = np.ascontiguousarray(np.array(v_l, dtype=np.float64))

    def add_submesh(self, faces, uvs):
        f_arr = np.ascontiguousarray(np.array(faces, dtype=np.int32))
        u_arr = np.ascontiguousarray(np.array(uvs, dtype=np.float64).reshape((-1, 3, 2)))
        # Default placeholder texture
        tex = np.zeros((128, 128, 3), dtype=np.uint8) + 150
        alpha = np.zeros((128, 128), dtype=np.uint8) + 255
        self.submeshes.append({'faces': f_arr, 'uvs': u_arr, 'tex': tex, 'alpha': alpha})

    def assign_texture(self, submesh_index, path):
        if 0 <= submesh_index < len(self.submeshes) and os.path.exists(path):
            img = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (256, 256))
            self.submeshes[submesh_index]['tex'] = np.ascontiguousarray(pygame.surfarray.pixels3d(img).astype(np.uint8))
            self.submeshes[submesh_index]['alpha'] = np.ascontiguousarray(pygame.surfarray.pixels_alpha(img).astype(np.uint8))

    def get_world_vertices(self):
        ax, ay, az = self.rot
        cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
        R = np.array([[cz*cy, cz*sy*sx-sz*cx, cz*sy*cx+sz*sx],
                      [sz*cy, sz*sy*sx+cz*cx, sz*sy*cx-cz*sx],
                      [-sy, cy*sx, cy*cx]])
        return (self.vertices * self.scale) @ R.T + self.pos

def run_engine():
    pygame.init()
    sw, sh = 256, 256
    screen_surf = pygame.Surface((sw, sh))
    display = pygame.display.set_mode((800, 800))
    clock = pygame.time.Clock()
    z_buffer = np.zeros((sw, sh), dtype=np.float32)

    teapot = Engine3D("testing/teapot.obj")
    # If your teapot has 2 parts, you'd call this for index 0 and 1
    teapot.assign_texture(0, "testing/default.png")
    teapot.scale = np.array([0.1, 0.1, 0.1])
    
    light1 = Engine3D("testing/cube.obj"); light1.is_light = True; light1.scale *= 0.3
    objects = [teapot, light1]
    cam_pos, cam_rot = np.array([0.0, 0.0, -15.0], dtype=np.float64), [0.0, 0.0]
    mouse_locked = False

    while True:
        dt = clock.tick() / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_locked = True
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                mouse_locked = False
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)

        # Light Orbit
        t = pygame.time.get_ticks() * 0.002
        light1.pos = np.array([math.sin(t)*7, math.cos(t*0.5)*5, math.cos(t)*7])

        if mouse_locked:
            mx, my = pygame.mouse.get_rel()
            cam_rot[0] += mx * 0.002
            cam_rot[1] -= my * 0.002

        lights = np.array([obj.pos for obj in objects if obj.is_light], dtype=np.float64)
        screen_surf.fill((10, 10, 20))
        z_buffer.fill(0.0)
        px_array = pygame.surfarray.pixels3d(screen_surf)
        
        c_y, s_y, c_p, s_p = math.cos(cam_rot[0]), math.sin(cam_rot[0]), math.cos(cam_rot[1]), math.sin(cam_rot[1])
        R_cam = np.array([[c_y, 0, s_y], [s_y*s_p, c_p, -c_y*s_p], [-s_y*c_p, s_p, c_y*c_p]])

        for obj in objects:
            v_world = obj.get_world_vertices()
            v_view = (v_world - cam_pos) @ R_cam.T
            zc = np.maximum(v_view[:, 2], 0.1)
            v_screen = np.empty_like(v_view)
            v_screen[:, 0] = v_view[:, 0] * (280.0 / zc) + (sw / 2)
            # FLIP: Subtract from center instead of adding to fix world orientation
            v_screen[:, 1] = (sh / 2) - v_view[:, 1] * (280.0 / zc) 
            v_screen[:, 2] = 1.0 / zc

            for mesh in obj.submeshes:
                render_submesh_numba(px_array, z_buffer, v_screen, v_world, mesh['faces'], mesh['uvs'],
                                     mesh['tex'], mesh['alpha'], sw, sh, True, lights, obj.is_light)

        display.blit(pygame.transform.scale(screen_surf, (800, 800)), (0, 0))
        pygame.display.set_caption(f"fps: {clock.get_fps()}")
        pygame.display.flip()

if __name__ == "__main__":
    run_engine()