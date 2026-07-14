# Blender Synthetic Objects Dataset

This dataset pairs 10 simple geometric shapes and 10 furniture models, each rendered in 10 distinct materials (wood, glass, metal, fabric, leather, plastic, etc.) from 10 angles around the object, plus a handful of full-scene overview shots. It's designed for tasks like material recognition, shape classification, and lighting/reflection studies, with labels encoded directly in the filenames.

The code to reproduce the Blender Synthetic Objects Dataset is available at [GitHub](https://github.com/SYadda/Blender_Synthetic_Objects_Dataset).


## Statistics

| Metric | Value |
|---|---|
| Object categories | 10 |
| Furniture categories | 10 |
| Materials | 10 |
| Angles per item | 10 (36° apart) |
| Single-item images | 20 × 10 × 10 = 2,000 |
| Global scene overview images | 10 (objects) + 10 (furniture) = 20 |
| **Total images** | **2,020** |

## Folder Layout

```
object/       # all geometric object renders
furniture/    # all furniture renders
```

## Naming Conventions

### Objects (`object/`)
- **Global scene images:** `obj_00_global_scene_angle_[0-9].png`
  e.g. `obj_00_global_scene_angle_0.png`
- **Single-object images:** `obj_[material]_[shape]_angle_[0-9].png`
  e.g. `obj_clear_glass_sphere_angle_3.png`

### Furniture (`furniture/`)
- **Global scene images:** `fur_00_global_scene_angle_[0-9].png`
  e.g. `fur_00_global_scene_angle_0.png`
- **Single-object images:** `fur_[material]_[shape]_angle_[0-9].png`
  e.g. `fur_clear_glass_sphere_angle_3.png`

## Materials

| Material | Base Color (RGBA) | Roughness | Metallic | Transmission | Description |
|---|---|---|---|---|---|
| `rough_oak` | (0.3, 0.15, 0.05, 1.0) | 0.80 | — | — | Matte, warm-brown wood with a coarse, non-reflective surface. |
| `clear_glass` | (1.0, 1.0, 1.0, 1.0) | 0.00 | — | 1.0 | Fully transparent, mirror-smooth glass. |
| `polished_steel` | (0.8, 0.8, 0.8, 1.0) | 0.05 | 1.0 | — | Bright, mirror-like metallic steel. |
| `rusted_iron` | (0.2, 0.05, 0.01, 1.0) | 0.90 | 0.5 | — | Dark, weathered metal with a dull, corroded finish. |
| `solid_gold` | (1.0, 0.7, 0.1, 1.0) | 0.15 | 1.0 | — | Shiny, warm-yellow polished gold. |
| `veined_marble` | (0.9, 0.9, 0.9, 1.0) | 0.20 | — | — | Light, off-white stone with a smooth, semi-glossy finish. |
| `carbon_fiber` | (0.05, 0.05, 0.05, 1.0) | 0.40 | 0.3 | — | Near-black, subtly metallic woven composite. |
| `blue_fabric` | (0.12, 0.22, 0.55, 1.0) | 0.95 | — | — | Soft, deep-blue cloth with a matte, non-reflective texture. |
| `brown_leather` | (0.28, 0.15, 0.08, 1.0) | 0.45 | — | — | Warm brown leather with a slight satin sheen. |
| `glossy_plastic` | (0.85, 0.05, 0.05, 1.0) | 0.12 | — | — | Bright red plastic with a smooth, glossy finish. |

## Shapes

| Shape | Description |
|---|---|
| `sphere` | A perfectly round ball. |
| `cube` | A six-sided box with square faces. |
| `cylinder` | A tube-like solid with two flat circular ends. |
| `torus` | A donut-shaped ring with a hole through the center. |
| `tetrahedron` | A four-sided solid made of triangular faces. |
| `cone` | A solid with a circular base tapering to a single point. |
| `icosphere` | A sphere approximated from many small triangular facets. |
| `octahedron` | An eight-sided solid formed by two square pyramids joined base to base. |
| `hex_prism` | A prism with hexagonal top and bottom faces. |
| `square_pyramid` | A pyramid with a square base tapering to a single apex. |

## Usage

This dataset is suitable for:
- Material recognition
- Shape classification
- Reflection / lighting studies
- Synthetic-to-real transfer experiments

File names encode material, shape, and angle — use these tokens to build labels and train/validation splits.

## Notes

- All renders were produced with Blender; lighting, camera, and ground plane setup are consistent across shots.
- Optional extras available on request: alternate thumbnail sizes, a paginated HTML gallery, or CSV label files.

## Dataset
You can access the complete Blender Synthetic Objects Dataset at Zenodo.

> Yuhang, D. (2026). Blender Synthetic Objects Dataset [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21355399

## References

- antonio36. (2019, November 20). *HomeDesk* [3D model]. Free3D. https://free3d.com/3d-model/home-desk-235534.html
- berkayc. (2019, November 20). *Sofa* [3D model]. Free3D. https://free3d.com/3d-model/sofa-801691.html
- deiamasc. (2021, April 15). *Cadeira* [3D model]. Free3D. https://free3d.com/3d-model/cadeira-378801.html
- denakrom. (2020, February 19). *SimpleDesk* [3D model]. Free3D. https://free3d.com/3d-model/simple-desk-258372.html
- darpor, a. (2020, January 3). *OfficeChair* [3D model]. Free3D. https://free3d.com/3d-model/office-chair-480392.html
- hermes25. (2019, November 20). *DesignChair* [3D model]. Free3D. https://free3d.com/3d-model/design-chair-38271.html
- hermes25. (2019, November 20). *DesignSofa* [3D model]. Free3D. https://free3d.com/3d-model/design-sofa-85845.html
- kpawlowicz. (2019, November 20). *SimpleWardrobe* [3D model]. Free3D. https://free3d.com/3d-model/simple-wardrobe-153178.html
- mitsui. (2020, October 14). *Table* [3D model]. Free3D. https://free3d.com/3d-model/table-747735.html
- vinitk. (2019, November 20). *Wardrobe4Doors* [3D model]. Free3D. https://free3d.com/3d-model/wardrobe-4-doors-755350.html
