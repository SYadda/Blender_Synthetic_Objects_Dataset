import bpy
import bmesh
import math
import os

TEST_MODE = False
OUTPUT_DIR = os.path.abspath("./d_primitives")
NUM_ANGLES = 10
SPACING = 6.0
TARGET_SIZE = 1.5  # Normalization target: bounding box diagonal length, ensures consistent visual size across different geometries

# Create the directory if it does not exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Clean up scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Use Cycles engine
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.cycles.device = 'GPU'
cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
cycles_prefs.compute_device_type = 'OPTIX'
cycles_prefs.get_devices()
for device in cycles_prefs.devices:
    if device.type == cycles_prefs.compute_device_type:
        device.use = True
        print(f"Enabled GPU Device ({device.type}): {device.name}")
    else:
        device.use = False

# ==========================================
# Environment Setup (HDRI / World)
# ==========================================
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

world.use_nodes = True
bg_tree = world.node_tree
bg_nodes = bg_tree.nodes
bg_links = bg_tree.links

bg_nodes.clear()

node_env = bg_nodes.new(type='ShaderNodeTexEnvironment')
node_bg = bg_nodes.new(type='ShaderNodeBackground')
node_out = bg_nodes.new(type='ShaderNodeOutputWorld')

bg_links.new(node_env.outputs['Color'], node_bg.inputs['Color'])
bg_links.new(node_bg.outputs['Background'], node_out.inputs['Surface'])

datafiles = bpy.utils.system_resource('DATAFILES')
# Use a clean studio environment without trees, to avoid tree reflections appearing on glass/metal reflective materials
hdri_path = os.path.join(datafiles, "studiolights", "world", "studio.exr")

if os.path.exists(hdri_path):
    node_env.image = bpy.data.images.load(hdri_path)
    node_bg.inputs['Strength'].default_value = 1.0
else:
    node_sky = bg_nodes.new(type='ShaderNodeTexSky')
    bg_links.new(node_sky.outputs['Color'], node_bg.inputs['Color'])

# ==========================================
# Material Definitions
# ==========================================
def set_bsdf_param(bsdf, key, value):
    if key in bsdf.inputs:
        bsdf.inputs[key].default_value = value
    elif key == "Transmission" and "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = value

def create_material(name, color, metallic=0.0, roughness=0.5, transmission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        set_bsdf_param(bsdf, "Base Color", color)
        set_bsdf_param(bsdf, "Metallic", metallic)
        set_bsdf_param(bsdf, "Roughness", roughness)
        set_bsdf_param(bsdf, "Transmission", transmission)
    return mat

materials_dict = {
    "rough_oak": create_material("rough_oak", (0.3, 0.15, 0.05, 1.0), roughness=0.8),
    "clear_glass": create_material("clear_glass", (1.0, 1.0, 1.0, 1.0), roughness=0.0, transmission=1.0),
    "polished_steel": create_material("polished_steel", (0.8, 0.8, 0.8, 1.0), metallic=1.0, roughness=0.05),
    "rusted_iron": create_material("rusted_iron", (0.2, 0.05, 0.01, 1.0), metallic=0.5, roughness=0.9),
    "solid_gold": create_material("solid_gold", (1.0, 0.7, 0.1, 1.0), metallic=1.0, roughness=0.15),
    "veined_marble": create_material("veined_marble", (0.9, 0.9, 0.9, 1.0), roughness=0.2),
    "carbon_fiber": create_material("carbon_fiber", (0.05, 0.05, 0.05, 1.0), metallic=0.3, roughness=0.4),
    "blue_fabric": create_material("blue_fabric", (0.12, 0.22, 0.55, 1.0), roughness=0.95),
    "brown_leather": create_material("brown_leather", (0.28, 0.15, 0.08, 1.0), roughness=0.45),
    "glossy_plastic": create_material("glossy_plastic", (0.85, 0.05, 0.05, 1.0), roughness=0.12),
}
mat_keys = list(materials_dict.keys())

# ==========================================
# Ten standard geometry generator functions
# ==========================================
def create_octahedron(name="Octahedron"):
    """Blender has no built-in octahedron generator, so construct it manually with bmesh"""
    verts = [
        (1, 0, 0), (-1, 0, 0),
        (0, 1, 0), (0, -1, 0),
        (0, 0, 1), (0, 0, -1),
    ]
    faces = [
        (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
        (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def add_sphere():
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=32, ring_count=16)
    return bpy.context.active_object

def add_cube():
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    return bpy.context.active_object

def add_cylinder():
    bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0, vertices=32)
    return bpy.context.active_object

def add_torus():
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.35,
                                      major_segments=48, minor_segments=16)
    return bpy.context.active_object

def add_tetrahedron():
    # Regular tetrahedron: a 3-sided cone with the tip radius collapsed to 0
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=1.0, radius2=0.0, depth=1.6)
    return bpy.context.active_object

def add_cone():
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1.0, radius2=0.0, depth=2.0)
    return bpy.context.active_object

def add_icosphere():
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, subdivisions=2)
    return bpy.context.active_object

def add_octahedron():
    return create_octahedron()

def add_hex_prism():
    # Hexagonal prism: cylinder with the number of sides changed to 6
    bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0, vertices=6)
    return bpy.context.active_object

def add_square_pyramid():
    # Square pyramid: a 4-sided cone with the tip radius collapsed to 0
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=1.0, radius2=0.0, depth=1.6)
    return bpy.context.active_object

SHAPE_GENERATORS = {
    "Sphere": add_sphere,
    "Cube": add_cube,
    "Cylinder": add_cylinder,
    "Torus": add_torus,
    "Tetrahedron": add_tetrahedron,
    "Cone": add_cone,
    "Icosphere": add_icosphere,
    "Octahedron": add_octahedron,
    "HexPrism": add_hex_prism,
    "SquarePyramid": add_square_pyramid,
}
shape_names = list(SHAPE_GENERATORS.keys())

# Smooth-shade curved geometries; keep flat shading for polyhedra (sharp edges)
SMOOTH_SHAPES = {"Sphere", "Cylinder", "Torus", "Cone", "Icosphere"}


def transform_point(matrix, point):
    x, y, z = point
    tx = matrix[0][0]*x + matrix[0][1]*y + matrix[0][2]*z + matrix[0][3]
    ty = matrix[1][0]*x + matrix[1][1]*y + matrix[1][2]*z + matrix[1][3]
    tz = matrix[2][0]*x + matrix[2][1]*y + matrix[2][2]*z + matrix[2][3]
    return (tx, ty, tz)


def get_world_bbox_diagonal(obj):
    mw = obj.matrix_world
    coords = [transform_point(mw, corner) for corner in obj.bound_box]
    xs = [c[0] for c in coords]; ys = [c[1] for c in coords]; zs = [c[2] for c in coords]
    size = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    return math.sqrt(size[0]**2 + size[1]**2 + size[2]**2)

# ==========================================
# Object Generation & Normalization
# ==========================================
all_objects = []

grid_center_x = ((len(shape_names) - 1) * SPACING) / 2.0
grid_center_y = ((len(mat_keys) - 1) * SPACING) / 2.0
grid_center = (grid_center_x, grid_center_y, 0)

for y, mat_name in enumerate(mat_keys):
    for x, shape_name in enumerate(shape_names):
        loc = (x * SPACING, y * SPACING, 0.0)

        obj = SHAPE_GENERATORS[shape_name]()
        obj.name = f"{mat_name}_{shape_name}"

        if shape_name in SMOOTH_SHAPES:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.shade_smooth()

        bpy.context.view_layer.update()

        # Normalize using the bounding box diagonal length, ensures consistent visual size across different geometries
        bbox_diagonal = get_world_bbox_diagonal(obj)
        if bbox_diagonal > 0.001:
            scale = TARGET_SIZE / bbox_diagonal
            obj.scale = (scale, scale, scale)

        obj.location = loc

        obj.data.materials.clear()
        obj.data.materials.append(materials_dict[mat_name])

        all_objects.append(obj)

# Add ground plane
bpy.ops.mesh.primitive_plane_add(size=200, location=(grid_center_x, grid_center_y, -0.01))
ground = bpy.context.view_layer.objects.active
ground.name = "GroundPlane"
ground_mat = bpy.data.materials.new(name="GroundMaterial")
ground_mat.use_nodes = True
ground_bsdf = ground_mat.node_tree.nodes.get('Principled BSDF')
if ground_bsdf:
    set_bsdf_param(ground_bsdf, "Base Color", (0.1, 0.1, 0.1, 1.0))
    set_bsdf_param(ground_bsdf, "Roughness", 0.8)
ground.data.materials.append(ground_mat)

# ==========================================
# Camera Setup
# ==========================================
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
pivot = bpy.context.view_layer.objects.active
pivot.name = "CameraPivot"

bpy.ops.object.camera_add(location=(0, -1, 1))
cam = bpy.context.view_layer.objects.active
cam.name = "RenderCamera"
bpy.context.scene.camera = cam

cam.parent = pivot

track = cam.constraints.new(type='TRACK_TO')
track.target = pivot
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

# ==========================================
# Rendering Logic
# ==========================================
def render_angles(target_location, distance, elevation, prefix):
    pivot.location = target_location
    cam.location = (0, -distance, elevation)

    if TEST_MODE:
        bpy.context.view_layer.update()
        filepath = os.path.join(OUTPUT_DIR, f"{prefix}.png")
        bpy.context.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        print(f"Rendered: {filepath}")
        return

    step_angle = 360.0 / NUM_ANGLES

    for i in range(NUM_ANGLES):
        pivot.rotation_euler[2] = math.radians(i * step_angle)
        bpy.context.view_layer.update()

        filepath = os.path.join(OUTPUT_DIR, f"{prefix}_angle_{i}.png")
        bpy.context.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        print(f"Rendered: {filepath}")

# 1. Render the overview scene (all objects visible)
if not TEST_MODE:
    global_dist = max(len(shape_names), len(mat_keys)) * SPACING * 1.6
    render_angles(
        target_location=grid_center,
        distance=global_dist,
        elevation=global_dist * 0.7,
        prefix="00_global_scene"
    )

# 2. Render individual geometry images
pivot.rotation_euler[2] = 0.0

# Hide all first
for o in all_objects:
    o.hide_render = True
    o.hide_viewport = True

# Show and render one by one
for obj in all_objects:
    obj.hide_render = False
    obj.hide_viewport = False

    individual_dist = TARGET_SIZE * 3.0
    render_angles(
        target_location=obj.location,
        distance=individual_dist,
        elevation=individual_dist * 0.8,
        prefix=f"obj_{obj.name}"
    )

    obj.hide_render = True
    obj.hide_viewport = True

# Restore visibility
for o in all_objects:
    o.hide_render = False
    o.hide_viewport = False

print(f"All rendering complete! Files saved to: {OUTPUT_DIR}")
