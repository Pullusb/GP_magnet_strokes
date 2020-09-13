# GP Magnet strokes

Magnet selected Grease pencil points to lines on other layers

**[Download latest](https://github.com/Pullusb/GP_magnet_strokes/archive/master.zip)**

<!-- ### [Demo Youtube]() -->

---  

## Description

This was made for magneting fill strokes (in dedicated color layer) on line strokes living on other layers.

How to use:  

Use a shortcut magnet selected lines on active layers on lines of other layers

You can filter by material names in the dedicated field separated by a ',' (case insensitive)  
To target all lines, just leave the field empty.

/!\ The magnet snapping happen in 2D screen space but will also change the depth of your moving stroke (those are aligned on the same depth as the one of the point in your selection)

### Where ?

Panel in sidebar : 3D view > sidebar ('N') > Gpencil  
Shortcut to trigger (temporary) : `F5`

<!--
## Todo:
- Autoclean overlapping output points locations
- Expose filter (authorize multiple filtering type) (or let it KISS ?)  
- authorize snapping on the same layer as option
- Brush mode... (complex, maybe on another version)
-  -->

---

## Changelog:

0.2.0:

- Working version with optional plain material name filter