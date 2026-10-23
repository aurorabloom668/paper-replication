# Coordinate systems

PiLoT supports two pose / map conventions. Pick the one that matches how your
3DGS map was trained.

## Normalized (SMBU / CityGaussian)

| Field | Format |
|-------|--------|
| Translation | `x y z` in normalized CityGaussian model coordinates (COLMAP-like; not inherently meters) |
| Rotation | `pitch roll yaw` degrees, xyz Euler |
| Pose line | `name x y z pitch roll yaw` |
| Renderer | `type: citygs` |
| Config flag | `coordinate_system: normalized` |

The map checkpoint and COLMAP sparse must come from the same CityGaussian training run. The normalization rescales the scene, so these coordinates have no universal conversion to meters. A metric scale or GPS/ECEF alignment is required before reporting translation errors in meters.

## ECEF (Feicuiwan / Jadebay)

| Field | Format |
|-------|--------|
| Translation | `lon lat alt` (WGS84 degrees + meters) |
| Rotation | `roll pitch yaw` degrees |
| Pose line | `name lon lat alt roll pitch yaw` |
| Renderer | `type: 3dgs` |
| Config flag | `coordinate_system: ecef` |

The PLY model uses a CGCS2000 offset (`cgcs_offset` in config); poses are converted internally.

## Switching backends

Only `render_config.type` and `coordinate_system` change between demos. The
localization stack (`main.py`, learned optimizer, feature extractor) is shared.
