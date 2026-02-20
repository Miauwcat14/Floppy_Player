import pygame
import numpy as np
from numba import njit, prange
import sys
import os
import math
import trimesh

@njit(fastmath=True, cache=True)
def draw_textured_triangle(px_array, z_buffer, v1, v2, v3, t1, t2, t3, texture, tex_alpha, sw, sh, intensity, wireframe_mode=False):
    # 1. Bounding Box Clamping
    min_x = int(max(0, math.floor(min(v1[0], v2[0], v3[0]))))
    max_x = int(min(sw - 1, math.ceil(max(v1[0], v2[0], v3[0]))))
    min_y = int(max(0, math.floor(min(v1[1], v2[1], v3[1]))))
    max_y = int(min(sh - 1, math.ceil(max(v1[1], v2[1], v3[1]))))

    den = (v2[1] - v3[1]) * (v1[0] - v3[0]) + (v3[0] - v2[0]) * (v1[1] - v3[1])
    if den == 0.0: return
    inv_den = 1.0 / den

    # Barycentric coefficients
    a1, b1 = (v2[1] - v3[1]) * inv_den, (v3[0] - v2[0]) * inv_den
    c1 = ((v2[1] - v3[1]) * (-v3[0]) + (v3[0] - v2[0]) * (-v3[1])) * inv_den
    a2, b2 = (v3[1] - v1[1]) * inv_den, (v1[0] - v3[0]) * inv_den
    c2 = ((v3[1] - v1[1]) * (-v3[0]) + (v1[0] - v3[0]) * (-v3[1])) * inv_den

    # --- PERSPECTIVE PREPARATION ---
    # In your engine, v[2] is already 1/Z (calculated in the main loop)
    invz1, invz2, invz3 = v1[2], v2[2], v3[2]
    
    # Pre-multiply UVs by their respective 1/Z
    u1z, v1z = t1[0] * invz1, t1[1] * invz1
    u2z, v2z = t2[0] * invz2, t2[1] * invz2
    u3z, v3z = t3[0] * invz3, t3[1] * invz3

    tw_f, th_f = float(texture.shape[0] - 1), float(texture.shape[1] - 1)
    tw_i, th_i = texture.shape[0], texture.shape[1]
    
    TILE_SIZE = 16

    for ty in range(min_y, max_y + 1, TILE_SIZE):
        for tx_tile in range(min_x, max_x + 1, TILE_SIZE):
            tile_max_x = min(tx_tile + TILE_SIZE - 1, max_x)
            tile_max_y = min(ty + TILE_SIZE - 1, max_y)
            
            # Tile Coarse Cull
            w1_c1 = a1 * tx_tile + b1 * ty + c1
            w2_c1 = a2 * tx_tile + b2 * ty + c2
            w1_c2 = a1 * tile_max_x + b1 * ty + c1
            w2_c2 = a2 * tile_max_x + b2 * ty + c2
            w1_c3 = a1 * tx_tile + b1 * tile_max_y + c1
            w2_c3 = a2 * tx_tile + b2 * tile_max_y + c2
            w1_c4 = a1 * tile_max_x + b1 * tile_max_y + c1
            w2_c4 = a2 * tile_max_x + b2 * tile_max_y + c2

            if (w1_c1 < 0 and w1_c2 < 0 and w1_c3 < 0 and w1_c4 < 0) or \
               (w2_c1 < 0 and w2_c2 < 0 and w2_c3 < 0 and w2_c4 < 0) or \
               ((1-w1_c1-w2_c1) < 0 and (1-w1_c2-w2_c2) < 0 and (1-w1_c3-w2_c3) < 0 and (1-w1_c4-w2_c4) < 0):
                continue

            for y in range(ty, tile_max_y + 1):
                w1_row = a1 * tx_tile + b1 * y + c1
                w2_row = a2 * tx_tile + b2 * y + c2
                
                for x in range(tx_tile, tile_max_x + 1):
                    w1, w2 = w1_row, w2_row
                    w3 = 1.0 - w1 - w2
                    
                    if w1 >= 0.0 and w2 >= 0.0 and w3 >= 0.0:
                        # 1. Interpolate 1/Z (This is used for the Z-Buffer)
                        interp_invz = w1 * invz1 + w2 * invz2 + w3 * invz3
                        
                        if interp_invz > z_buffer[x, y]:
                            if wireframe_mode:
                                if w1 < 0.03 or w2 < 0.03 or w3 < 0.03:
                                    f_int = 2.0
                                else:
                                    w1_row += a1
                                    w2_row += a2
                                    continue
                            else:
                                f_int = intensity

                            # 2. Interpolate U/Z and V/Z
                            interp_uz = w1 * u1z + w2 * u2z + w3 * u3z
                            interp_vz = w1 * v1z + w2 * v2z + w3 * v3z

                            # 3. Project back to 2D texture space
                            # UV = (U/Z) / (1/Z)
                            z_real = 1.0 / interp_invz
                            u = (interp_uz * z_real) * tw_f
                            v = (interp_vz * z_real) * th_f
                            
                            sam_x, sam_y = int(u) % tw_i, int(v) % th_i
                            
                            if tex_alpha[sam_x, sam_y] > 128:
                                z_buffer[x, y] = interp_invz
                                c_val = min(1.0, f_int)
                                px_array[x, y, 0] = np.uint8(texture[sam_x, sam_y, 0] * c_val)
                                px_array[x, y, 1] = np.uint8(texture[sam_x, sam_y, 1] * c_val)
                                px_array[x, y, 2] = np.uint8(texture[sam_x, sam_y, 2] * c_val)
                    
                    w1_row += a1
                    w2_row += a2

@njit(parallel=True, fastmath=True, cache=True)
def render_submesh_numba(px_array, z_buffer, v_arr, v_world, faces, face_uvs, texture, tex_alpha, sw, sh, cull, lights, is_light, wireframe_mode):
    for i in prange(faces.shape[0]):
        v1, v2, v3 = v_arr[faces[i,0]], v_arr[faces[i,1]], v_arr[faces[i,2]]
        
        if v1[2] <= 0 or v2[2] <= 0 or v3[2] <= 0:
            continue

        # Backface culling
        if cull and not is_light:
            if (v2[0]-v1[0])*(v3[1]-v1[1]) - (v2[1]-v1[1])*(v3[0]-v1[0]) <= 0: 
                continue

        p1w, p2w, p3w = v_world[faces[i,0]], v_world[faces[i,1]], v_world[faces[i,2]]
        
        # Lighting
        if is_light:
            intensity = 1.0
        else:
            normal = np.cross(p2w - p1w, p3w - p1w).astype(np.float32)
            n_len = np.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
            if n_len == 0: continue
            normal /= n_len
            
            face_center = (p1w + p2w + p3w) / 3.0
            intensity = 0.4
            for j in range(lights.shape[0]):
                l_dir = lights[j] - face_center
                l_dist_sq = l_dir[0]**2 + l_dir[1]**2 + l_dir[2]**2
                l_dist = np.sqrt(l_dist_sq)
                if l_dist != 0:
                    dot = np.dot(normal, l_dir.astype(np.float32)) / l_dist
                    intensity += max(0.0, dot) * (1.0 / (1.0 + 0.01 * l_dist + 0.002 * l_dist_sq))

        draw_textured_triangle(px_array, z_buffer, v1, v2, v3, face_uvs[i,0], face_uvs[i,1], face_uvs[i,2], 
                               texture, tex_alpha, sw, sh, intensity, wireframe_mode)

class Engine3D:
    def __init__(self, path=None):
        self.bounding_radius = 0.0
        self.vertices = np.empty((0,3), dtype=np.float64)
        self.submeshes = []
        self.pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.rot = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.scale = np.array([1.0, 1.0, 1.0], dtype=np.float64)
        self.is_light = False
        self.wireframe = False  # Wireframe toggle
        self.cull_backfaces = True  # Backface culling toggle
        # Skeletal animation preparation
        self.vertex_weights = np.empty((0, 4), dtype=np.float64)  # Max 4 bone influences per vertex
        self.bone_ids = np.empty((0, 4), dtype=np.int32)  # Max 4 bone IDs per vertex
        if path: 
            if path == "internal_cube":
                self.create_internal_cube()
            elif path == "blender_grid":
                self.create_blender_grid()
            else:
                self.load_with_trimesh(path)
            self._calculate_bounds()

    def _calculate_bounds(self):
        if len(self.vertices) > 0:
            # Calculate distance of each vertex from local (0,0,0)
            distances = np.sqrt(np.sum(self.vertices**2, axis=1))
            self.bounding_radius = np.max(distances)

    def is_in_frustum(self, cam_pos, R_cam, sw, sh):
        rel_pos = self.pos - cam_pos
        view_pos = rel_pos @ R_cam.T
        
        z = view_pos[2]
        r = self.bounding_radius * np.max(self.scale)

        # 1. Near plane check (Z > 0)
        if z + r < 0.1: 
            return False
        h_margin = (sw / 2.0) * (z / 280.0) + r
        if abs(view_pos[0]) > h_margin:
            return False

        v_margin = (sh / 2.0) * (z / 280.0) + r
        if abs(view_pos[1]) > v_margin:
            return False

        return True

    def create_blender_grid(self):
        # Create Blender-style grid lines from -10 to 10
        grid_size = 20.0
        grid_step = 2.0
        grid_color = np.array([120, 120, 120], dtype=np.uint8)  # Light grey
        
        vertices = []
        faces = []
        
        # Generate grid line vertices
        line_vertices = []
        
        # Horizontal lines (along X axis)
        for i in np.arange(-grid_size/2, grid_size/2 + grid_step, grid_step):
            # Line from (-grid_size/2, 0, i) to (grid_size/2, 0, i)
            v1 = np.array([-grid_size/2, 0.0, i])
            v2 = np.array([grid_size/2, 0.0, i])
            
            # Create thin rectangle for line
            thickness = 0.05
            offset = np.array([0.0, 0.0, thickness])
            
            rect_verts = [
                v1 - offset, v1 + offset,
                v2 + offset, v2 - offset
            ]
            line_vertices.extend(rect_verts)
            
            base_idx = len(line_vertices) - 4
            faces.extend([
                [base_idx, base_idx + 1, base_idx + 2],
                [base_idx, base_idx + 2, base_idx + 3]
            ])
        
        # Vertical lines (along Z axis)  
        for i in np.arange(-grid_size/2, grid_size/2 + grid_step, grid_step):
            # Line from (i, 0, -grid_size/2) to (i, 0, grid_size/2)
            v1 = np.array([i, 0.0, -grid_size/2])
            v2 = np.array([i, 0.0, grid_size/2])
            
            # Create thin rectangle for line
            thickness = 0.05
            offset = np.array([thickness, 0.0, 0.0])
            
            rect_verts = [
                v1 - offset, v1 + offset,
                v2 + offset, v2 - offset
            ]
            line_vertices.extend(rect_verts)
            
            base_idx = len(line_vertices) - 4
            faces.extend([
                [base_idx, base_idx + 1, base_idx + 2],
                [base_idx, base_idx + 2, base_idx + 3]
            ])
        
        vertices = np.array(line_vertices, dtype=np.float64)
        faces = np.array(faces, dtype=np.int32)
        
        # Create UVs for grid lines
        face_uvs = np.zeros((len(faces), 3, 2), dtype=np.float64)
        
        self.vertices = np.ascontiguousarray(vertices)
        self.submeshes.append({
            'faces': np.ascontiguousarray(faces), 
            'uvs': np.ascontiguousarray(face_uvs), 
            'tex': np.ascontiguousarray(np.full((128, 128, 3), grid_color, dtype=np.uint8)), 
            'alpha': np.ascontiguousarray(np.full((128, 128), 255, dtype=np.uint8))
        })

    def create_internal_cube(self):
        # Generate internal cube using trimesh
        geometry = trimesh.creation.box(extents=(1, 1, 1))
        
        self.vertices = np.ascontiguousarray(geometry.vertices.astype(np.float64))
        faces = np.ascontiguousarray(geometry.faces.astype(np.int32))
        
        # Generate default UVs for cube
        face_uvs = np.ascontiguousarray(np.zeros((len(faces), 3, 2), dtype=np.float64))
        
        self.submeshes.append({
            'faces': faces, 
            'uvs': face_uvs, 
            'tex': np.ascontiguousarray(np.zeros((128, 128, 3), dtype=np.uint8) + 150), 
            'alpha': np.ascontiguousarray(np.zeros((128, 128), dtype=np.uint8) + 255)
        })

    def load_with_trimesh(self, path):
        mesh_data = trimesh.load(path)
        
        # Handle Scene objects by merging all geometries
        if isinstance(mesh_data, trimesh.Scene):
            # Get all geometries and merge them
            geometries = []
            for geom in mesh_data.geometry.values():
                if isinstance(geom, trimesh.Trimesh):
                    geometries.append(geom)
            
            if geometries:
                # Merge all geometries into one
                geometry = trimesh.util.concatenate(geometries)
            else:
                raise ValueError("No valid mesh geometries found in scene")
        else:
            geometry = mesh_data
        
        # Fix normals to ensure they point outward
        geometry.fix_normals()
        
        # We DO NOT subtract the center here, to keep it "natural" like your old version
        self.vertices = np.ascontiguousarray(geometry.vertices.astype(np.float64))
        
        faces = np.ascontiguousarray(geometry.faces.astype(np.int32))
        
        # Check for skeletal animation data (vertex attributes)
        if hasattr(geometry, 'vertex_attributes'):
            attrs = geometry.vertex_attributes
            if 'joint' in attrs or 'weight' in attrs:
                # Extract bone weights and IDs if available
                if 'weight' in attrs:
                    weights = attrs['weight']
                    if len(weights.shape) == 2 and weights.shape[1] >= 4:
                        self.vertex_weights = np.ascontiguousarray(weights[:, :4].astype(np.float64))
                    else:
                        self.vertex_weights = np.ascontiguousarray(np.zeros((len(self.vertices), 4), dtype=np.float64))
                
                if 'joint' in attrs:
                    joints = attrs['joint']
                    if len(joints.shape) == 2 and joints.shape[1] >= 4:
                        self.bone_ids = np.ascontiguousarray(joints[:, :4].astype(np.int32))
                    else:
                        self.bone_ids = np.ascontiguousarray(np.zeros((len(self.vertices), 4), dtype=np.int32))
        else:
            # Initialize empty skeletal data
            self.vertex_weights = np.ascontiguousarray(np.zeros((len(self.vertices), 4), dtype=np.float64))
            self.bone_ids = np.ascontiguousarray(np.zeros((len(self.vertices), 4), dtype=np.int32))
        
        # Handle UV mapping correctly
        if hasattr(geometry.visual, 'uv') and geometry.visual.uv is not None:
            u_arr = np.ascontiguousarray(geometry.visual.uv.astype(np.float64))
            u_arr[:, 1] = 1.0 - u_arr[:, 1] # Flip UV Y for Pygame
            # Ensure proper shape (N, 3, 2) for Numba function
            face_uvs = np.ascontiguousarray(u_arr[faces].reshape((-1, 3, 2)))
        else:
            face_uvs = np.ascontiguousarray(np.zeros((len(faces), 3, 2), dtype=np.float64))

        # Create checkerboard default texture for better visibility
        checkerboard = np.zeros((128, 128, 3), dtype=np.uint8)
        for i in range(128):
            for j in range(128):
                if (i // 16 + j // 16) % 2 == 0:
                    checkerboard[i, j] = [200, 200, 200]  # White squares
                else:
                    checkerboard[i, j] = [50, 50, 50]   # Black squares
        
        self.submeshes.append({
            'faces': faces, 
            'uvs': face_uvs, 
            'tex': np.ascontiguousarray(checkerboard), 
            'alpha': np.ascontiguousarray(np.full((128, 128), 255, dtype=np.uint8))
        })

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

    grid = Engine3D("blender_grid")
    
    teapot = Engine3D("testing/teapot.obj")
    # If your teapot has 2 parts, you'd call this for index 0 and 1
    teapot.assign_texture(0, "testing/default.png")
    teapot.scale = np.array([0.1, 0.1, 0.1])
    
    light1 = Engine3D("internal_cube")
    light1.is_light = True
    light1.scale *= 0.3
    objects = [grid, teapot, light1]
    # Blender-style orbit camera
    camera_distance = 20.0
    yaw = 0.0
    pitch = 0.0
    mouse_locked = False

    while True:
        dt = clock.tick() / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            # Mouse wheel for zoom
            if event.type == pygame.MOUSEWHEEL:
                camera_distance = max(5.0, min(50.0, camera_distance - event.y * 2.0))
            
            # Mouse buttons 4/5 for zoom
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Scroll up
                    camera_distance = max(5.0, camera_distance - 1.0)
                elif event.button == 5:  # Scroll down
                    camera_distance = min(50.0, camera_distance + 1.0)
            
            # Mouse drag for orbit
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_locked = True
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                mouse_locked = False
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
            # Wireframe toggle
            if event.type == pygame.KEYDOWN and event.key == pygame.K_k:
                for obj in objects:
                    obj.wireframe = not obj.wireframe
            # Backface culling toggle
            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                for obj in objects:
                    obj.cull_backfaces = not obj.cull_backfaces

        # Dynamic light orbit around teapot
        t = pygame.time.get_ticks() * 0.001
        radius = 8.0
        light1.pos = np.array([
            math.sin(t) * radius,  # X: circle movement
            3.0,                    # Y: fixed height above teapot
            math.cos(t) * radius   # Z: circle movement
        ])

        # Mouse input for orbit
        if mouse_locked:
            mx, my = pygame.mouse.get_rel()
            yaw += mx * 0.01
            pitch = max(-1.5, min(1.5, pitch + my * 0.01))
        
        # Calculate camera position from spherical coordinates (exact formulas)
        cam_pos = np.array([
            camera_distance * math.cos(pitch) * math.sin(yaw),   # X
            camera_distance * math.sin(pitch),                    # Y  
            -camera_distance * math.cos(pitch) * math.cos(yaw)    # Z (negative for forward)
        ], dtype=np.float64)

        lights = np.array([obj.pos for obj in objects if obj.is_light], dtype=np.float64)
        # Clear buffers each frame to prevent ghosting
        screen_surf.fill((10, 10, 20))
        z_buffer.fill(0.0)
        # Ensure px_array is properly accessed each frame
        px_array = pygame.surfarray.pixels3d(screen_surf)
        
        # Look-At Matrix (exact structure)
        Forward = -cam_pos / np.linalg.norm(cam_pos)
        Right = np.cross([0, 1, 0], Forward)
        Right /= np.linalg.norm(Right)
        Up = np.cross(Forward, Right)
        R_cam = np.stack([Right, Up, Forward])

        for obj in objects:
            if not obj.is_in_frustum(cam_pos, R_cam, sw, sh):
                continue
            v_world = obj.get_world_vertices()
            v_view = (v_world - cam_pos) @ R_cam.T
            zc = np.maximum(v_view[:, 2], 0.1)
            # Y-up, Z-forward coordinate system with proper centering
            v_screen = np.empty_like(v_view)
            v_screen[:, 0] = v_view[:, 0] * (280.0 / zc) + (sw / 2)  # X: centered
            v_screen[:, 1] = (sh / 2) - v_view[:, 1] * (280.0 / zc)  # Y: centered, flipped for screen coords
            v_screen[:, 2] = 1.0 / zc

            for mesh in obj.submeshes:
                render_submesh_numba(px_array, z_buffer, v_screen, v_world, mesh['faces'], mesh['uvs'],
                                     mesh['tex'], mesh['alpha'], sw, sh, obj.cull_backfaces, lights, obj.is_light, obj.wireframe)

        display.blit(pygame.transform.scale(screen_surf, (800, 800)), (0, 0))
        pygame.display.set_caption(f"fps: {clock.get_fps()}")
        pygame.display.flip()

if __name__ == "__main__":
    run_engine()