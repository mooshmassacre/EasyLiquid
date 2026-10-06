# EasyLiquid v1.3

Procedural fake liquid for Cinema 4D. Supports parametric cylinders and cubes.

<p align="center">
  <img src="docs/interface.png" alt="EasyLiquid v1.3 interface in Cinema 4D">
</p>

Select your object, choose a mode, and create the liquid. Adjust the settings in one compact panel.

*EasyLiquid v1.3 running in Cinema 4D.*

## Install or update

Download the installation ZIP from [Releases](https://github.com/mooshmassacre/EasyLiquid/releases).

1. Close Cinema 4D.
2. Replace the previous EasyLiquid folder in your Cinema 4D plugins directory with the EasyLiquid folder from this package. Keep only one installed copy.
3. Restart Cinema 4D and open Extensions > EasyLiquid v1.3.

## Use

Select a cylinder or cube, choose Continuous Waves or Motion Response, and click Create / Update Liquid. Animate the original object or its parent Null. Adjust the controls and click Apply Changes. Select an existing liquid and use Load from Selection to read its settings.

Keep Surface Level in World Space compensates for container rotation while preserving waves. Motion Response uses keyframed Position on the object or its parents. Transition Lead starts the wave release earlier during a curved stop.

For existing scenes, select the liquid and click Create / Update Liquid to update its tag and translate its User Data. Values are retained. Save a copy of important scenes before updating.

## v1.3 changes

English panel, User Data, mode names, messages, and help. Four separated sections, 12 px outer margins, compact 20 px icons, moderate row spacing, and paired settings buttons. Surface options share one row. Numeric inputs use a fixed 54 px width; sliders expand independently. Animation behavior is unchanged.

## Validation and limits

Source syntax checked. All 13 numeric input and slider pairs were checked for synchronization in both directions outside Cinema 4D. Layout uses native GeDialog grouping and spacing APIs documented by Maxon: https://developers.maxon.net/docs/py/2024_3_0/modules/c4d.gui/GeDialog/index.html
The preceding v1.1 engine was tested in Cinema 4D 2024.2.0. Native visual validation of this revised panel could not be completed in this session because UI automation could not focus the Script Manager.

This is an independent prototype, not affiliated with or endorsed by Maxon. Plugin ID 10691010 must be replaced with a registered Maxon ID before public distribution. It is a fake liquid mesh, without physical simulation or spills. Level compensation is intended for moderate container tilts.

## Source layout

- `EasyLiquid/EasyLiquid.pyp`: plugin registration.
- `EasyLiquid/plugin.py`: panel and commands.
- `EasyLiquid/engine.py`: geometry creation and embedded animation tag.
- `EasyLiquid/res/`: plugin and control icons.

Copy the `EasyLiquid` directory to your Cinema 4D plugins directory when installing from source. Do not run the `.pyp` file from Script Manager.

## Feedback

Report problems through Issues. Include your Cinema 4D version, the selected primitive, animation mode, reproduction steps, and any Python console error.
