# GP Magnet strokes

Magnet selected Grease pencil points to lines on other layers

/!\ Alpha, work in progress

**[Download latest](https://github.com/Pullusb/GP_magnet_strokes/archive/master.zip)**

<!-- ### [Demo Youtube]() -->

---  

## Description

This was made for magneting fill strokes (in dedicated color layer) on line strokes living on other layers.

Source scope:
    - Paint mode : last stroke only
    - Edit mode : Selected points (On active layer only !)

How to use:  

Use a shortcut magnet selected lines on active layers on lines of other layers

You can filter by material names in the dedicated field separated by a ',' (case insensitive)  
To target all lines, just leave the field empty.

/!\ The magnet snapping happen in 2D screen space but will also change the depth of your moving stroke.  
Those are aligned on the same depth as the one of the point in your selection.  
It does not auto reproject onthe drawing plane ! (for now)  

### Where ?

Panel in sidebar : 3D view > sidebar ('N') > Gpencil  
Shortcut to trigger (temporary) : `F5`

<!--
## Todo:
- resample on the fly
- resample shortcut ?
- authorize snapping on the same layer as option
- Brush mode... (complex, maybe on another version)
-  -->

<!-- ## Done
- Autoclean overlapping output points locations -->

---

## Changelog:

1.5.0:

- Better brush behavior: modify only brushed points instead of magnetize whole selection
- Better sculpt brush feel: drag point instead of stick, basic linear falloff)
- key: pressing `M` toggle point/line magnet during the modal

1.4.0:

- feat: new _brush_ magnet mode

1.3.0:

- feat: work directly on last stroke in paint mode

1.2.1:

- fix: view plane normal projection in VIEW orientation mode

1.2.0:

- Cleanup : Overlapping output points doubles deleted
- Point magnet mode: snap directly on points instead of lines, added as an option, off by default  

1.1.0:

- Correct end points depth (raycast on chosen drawing plane)
- handle distance: Proximity magnet with tolerance value
- lock magneted points with Ctrl (while moving)


1.0.0:

- Expose filter (multiple filtering type)

0.2.0:

- Working version with optional plain material name filter