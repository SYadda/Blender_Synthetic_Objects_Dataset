import bpy
import math
import os

TEST_MODE = False
OUTPUT_DIR = os.path.abspath("./furniture")
NUM_ANGLES = 10
SPACING = 6.0    
TARGET_SIZE = 1.5  # Normalization target: bounding box diagonal length (rather than a single longest edge), ensures consistent visual size across different furniture
BLEND_DIR = os.path.abspath("./blend")  # Folder that stores the furniture model files

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

# Insert a "multiply" color node between the environment texture and background
# to darken the pure white background to light gray, preventing white-material
# furniture from blending into the background and becoming hard to distinguish
node_tint = bg_nodes.new(type='ShaderNodeMixRGB')
node_tint.blend_type = 'MULTIPLY'
node_tint.inputs['Fac'].default_value = 1.0
node_tint.inputs['Color2'].default_value = (0.75, 0.75, 0.75, 1.0)  # Light gray, darkens the white background

bg_links.new(node_env.outputs['Color'], node_tint.inputs['Color1'])
bg_links.new(node_tint.outputs['Color'], node_bg.inputs['Color'])
bg_links.new(node_bg.outputs['Background'], node_out.inputs['Surface'])

datafiles = bpy.utils.system_resource('DATAFILES')
# Use a clean studio environment without trees, to avoid tree reflections appearing on glass/metal reflective materials
hdri_path = os.path.join(datafiles, "studiolights", "world", "studio.exr")

if os.path.exists(hdri_path):
    node_env.image = bpy.data.images.load(hdri_path)
    node_bg.inputs['Strength'].default_value = 1.0
else:
    node_sky = bg_nodes.new(type='ShaderNodeTexSky')
    bg_links.new(node_sky.outputs['Color'], node_tint.inputs['Color1'])

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
        set_bsdf_param(bsdf, "Metallic", metallic)  # Typo fixed
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
    "blue_fabric": create_material("blue_fabric", (0.12, 0.22, 0.55, 1.0), roughness=0.95),     # Fabric, non-metal, extremely rough, matte
    "brown_leather": create_material("brown_leather", (0.28, 0.15, 0.08, 1.0), roughness=0.45), # Leather, non-metal, medium gloss
    "glossy_plastic": create_material("glossy_plastic", (0.85, 0.05, 0.05, 1.0), roughness=0.12) # Glossy plastic, non-metal, highly glossy vivid color
}

furniture_types = ['DesignChair', 'OfficeChair', 'CadeirEstf', 'Sofa', 'DesignSofa', 'HomeDesk', 'SimpleDesk', 'Table', 'Wardrobe4Door', 'Wardrobe']
mat_keys = list(materials_dict.keys())

# ==========================================
# Base plate / display stand filter configuration
# ==========================================
# Objects whose name contains any of the following keywords (case-insensitive)
# are treated as base plates/display stands and skipped during import
BASE_KEYWORDS = [
    'base', 'floor', 'ground', 'plate', 'platform', 'pedestal',
    'stand', 'backdrop', 'display', 'plinth'
]

# Geometric fallback check: even if the name doesn't contain a keyword, if a mesh
# is extremely flat (thickness much smaller than length/width) and its horizontal
# projected area is clearly larger than the median of the other meshes in the batch,
# it is still classified as a base plate and removed
FLATNESS_THICKNESS_RATIO = 0.03   # thickness / max horizontal dimension below this ratio is considered "flat"
AREA_RATIO_THRESHOLD = 2.5        # projected area / median area of other meshes above this ratio is considered "clearly oversized"


def transform_point(matrix, point):
    x, y, z = point
    tx = matrix[0][0]*x + matrix[0][1]*y + matrix[0][2]*z + matrix[0][3]
    ty = matrix[1][0]*x + matrix[1][1]*y + matrix[1][2]*z + matrix[1][3]
    tz = matrix[2][0]*x + matrix[2][1]*y + matrix[2][2]*z + matrix[2][3]
    return (tx, ty, tz)


def get_world_bbox(obj):
    mw = obj.matrix_world
    coords = [transform_point(mw, corner) for corner in obj.bound_box]
    xs = [c[0] for c in coords]; ys = [c[1] for c in coords]; zs = [c[2] for c in coords]
    return (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))


def is_base_by_name(obj):
    name_lower = obj.name.lower()
    return any(k.lower() in name_lower for k in BASE_KEYWORDS)


def filter_out_base_objects(imported_objs):
    """Remove base plate/display stand type objects from the imported object list, return the filtered list"""
    bpy.context.view_layer.update()

    keep = []
    name_flagged = []
    for o in imported_objs:
        if o.type == 'MESH' and is_base_by_name(o):
            name_flagged.append(o)
        else:
            keep.append(o)

    # Geometric fallback: only evaluate when there are multiple meshes left,
    # to avoid mistakenly removing the furniture's only main body
    mesh_keep = [o for o in keep if o.type == 'MESH']
    if len(mesh_keep) > 1:
        infos = []
        for o in mesh_keep:
            sx, sy, sz = get_world_bbox(o)
            horiz_max = max(sx, sy)
            area = sx * sy
            infos.append((o, sz, horiz_max, area))

        areas_sorted = sorted(i[3] for i in infos)
        mid = len(areas_sorted) // 2
        median_area = areas_sorted[mid] if len(areas_sorted) % 2 == 1 else \
            (areas_sorted[mid - 1] + areas_sorted[mid]) / 2.0

        geo_flagged = []
        for o, sz, horiz_max, area in infos:
            if horiz_max <= 0:
                continue
            is_flat = (sz / horiz_max) < FLATNESS_THICKNESS_RATIO
            is_oversized = median_area > 0 and (area / median_area) > AREA_RATIO_THRESHOLD
            if is_flat and is_oversized:
                geo_flagged.append(o)

        if geo_flagged:
            keep = [o for o in keep if o not in geo_flagged]
            name_flagged.extend(geo_flagged)

    if name_flagged:
        print(f"  Skipped base plate/display stand objects: {[o.name for o in name_flagged]}")

    # Remove the excluded objects and their scene data to avoid leftovers
    for o in name_flagged:
        try:
            mesh_data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if mesh_data and mesh_data.users == 0:
                bpy.data.meshes.remove(mesh_data)
        except Exception:
            pass

    return keep

# ==========================================
# Object Generation & Normalization
# ==========================================
all_objects = []

grid_center_x = ((len(furniture_types) - 1) * SPACING) / 2.0
grid_center_y = ((len(mat_keys) - 1) * SPACING) / 2.0
grid_center = (grid_center_x, grid_center_y, 0)

for y, mat_name in enumerate(mat_keys):
    for x, furniture in enumerate(furniture_types):
        loc = (x * SPACING, y * SPACING, 0.0)
        blend_file_path = os.path.join(BLEND_DIR, f"{furniture}.blend")
        
        if os.path.exists(blend_file_path):
            try:
                with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
                    data_to.objects = data_from.objects  # import all objects

                imported_objs = [o for o in data_to.objects if o is not None]
                if not imported_objs:
                    continue

                # Link all of them into the scene
                for o in imported_objs:
                    bpy.context.collection.objects.link(o)

                # Exclude base plate/display stand type objects, do not import them
                imported_objs = filter_out_base_objects(imported_objs)
                if not imported_objs:
                    print(f"Warning: {furniture} has no remaining objects after filtering out base plates, skipping")
                    continue

                # Find root nodes (objects with no parent, or whose parent is not in the imported list)
                roots = [o for o in imported_objs if o.parent is None or o.parent not in imported_objs]

                # Create an empty object as a unified container, for convenient overall scaling/moving/renaming
                bpy.ops.object.empty_add(type='PLAIN_AXES')
                container = bpy.context.active_object
                container.name = f"{mat_name}_{furniture}"
                for r in roots:
                    r.parent = container

                # Compute the overall size from the world-space bounding box of all meshes,
                # rather than the .dimensions of a single object
                mesh_objs = [o for o in imported_objs if o.type == 'MESH']
                if not mesh_objs:
                    continue

                bpy.context.view_layer.update()

                coords = []
                for o in mesh_objs:
                    mw = o.matrix_world
                    for corner in o.bound_box:
                        coords.append(transform_point(mw, corner))
                xs = [c[0] for c in coords]; ys = [c[1] for c in coords]; zs = [c[2] for c in coords]
                size = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
                # Normalize using the bounding box diagonal length (rather than a single longest edge),
                # so that even when different furniture pieces have very different length/width/height
                # ratios (e.g. a tall, narrow wardrobe vs. a wide, short table), the overall visual
                # size stays close to consistent after normalization
                bbox_diagonal = math.sqrt(size[0]**2 + size[1]**2 + size[2]**2)

                if bbox_diagonal > 0.001:
                    scale = TARGET_SIZE / bbox_diagonal
                    container.scale = (scale, scale, scale)

                container.location = loc

                # Materials must be applied to all meshes, not just one
                for o in mesh_objs:
                    o.data.materials.clear()
                    o.data.materials.append(materials_dict[mat_name])

                all_objects.append(container)
                
            except Exception as e:
                print(f"Error processing {furniture} from {blend_file_path}: {e}")
        else:
            print(f"Warning: File not found: {blend_file_path}")

# Add ground plane
bpy.ops.mesh.primitive_plane_add(size=200, location=(grid_center_x, grid_center_y, -0.01)) # Increase ground plane size to accommodate the large spacing
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
    # [Optimization] Since the grid spacing (SPACING) is larger, multiply the camera
    # distance by 1.6x to prevent objects from overflowing the screen
    global_dist = max(len(furniture_types), len(mat_keys)) * SPACING * 1.6
    render_angles(
        target_location=grid_center, 
        distance=global_dist, 
        elevation=global_dist * 0.7, 
        prefix="00_global_scene"
    )

# 2. Render individual furniture images
pivot.rotation_euler[2] = 0.0

# Hide all first
for o in all_objects:
    o.hide_render = True
    o.hide_viewport = True

# Show and render one by one
for obj in all_objects:
    obj.hide_render = False
    obj.hide_viewport = False
    
    # For individual rendering, keep the camera distance appropriately matched to the object size
    individual_dist = TARGET_SIZE * 3.0 
    render_angles(
        target_location=obj.location, 
        distance=individual_dist, 
        elevation=individual_dist * 0.8, 
        prefix=f"fur_{obj.name}"
    )
    
    obj.hide_render = True
    obj.hide_viewport = True

# Restore visibility
for o in all_objects:
    o.hide_render = False
    o.hide_viewport = False

print(f"All rendering complete! Files saved to: {OUTPUT_DIR}")