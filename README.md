# GP Magnet strokes

Magnet selected Grease pencil points to lines on other layers

**[Download latest](https://github.com/Pullusb/GP_magnet_strokes/archive/master.zip)**

### [Tuto/Demo Youtube](https://youtu.be/_MZjbfNJqdQ)

Want to support me coding free tools ? [Check this page](http://www.samuelbernou.fr/donate)

---  

## Description

This was made for magneting fill strokes (in dedicated color layer) on line strokes living on other layers.

![magnet gif](https://raw.githubusercontent.com/Pullusb/images_repo/master/magnet_brush2.gif)

### Operators

Source scope:  
  - Paint mode : last stroke only
  - Edit mode : Selected points (only on active layer, you can select stroke on other layers)

Panel in sidebar : 3D view > sidebar ('N') > Gpencil  
<!-- Shortcut to trigger (temporary) : `F5` -->


**Magnet** : Perform operation once with current settings on all selection

**Magnet Brush** : Launch a modal allowing to sculpt

Shortcut available during brush modal :  
`F` : resize brush  
`shift` + `F` : resize magnet influence  
`M` : switch between line and point magnet  


### Options

**Near Layers Targets** : Magnet on lines from X layers above (or below if negative), 0 means all (disable the filter)  
hint: to check all top layers use big value so it counts all the above

**Materials Targets** : Filter lines by material names in field separated by a ',' (case insensitive)  
To target all lines, just leave the field empty.

**Magnet on selection** : Target only selected stroke (improve performance a lot as only selection is avluated)  

**Snap on point** (switch during modal with `M`) : Magnet on points instead of lines (faster)

**Display Position** : Overlay to show actual point position (pre-snap computation) to see what to "sculpt"


### Notes

- Magnet is limited to stroke visible on screen for performance.  
If the magnet is very slow, try zooming on the area you need to snap on.

- All filters are cumulative

- The magnet snapping happen in 2D screen space but change the depth of your moving stroke.  
It perform an auto reprojection at the end of the edit according to your current GP projection settings.


> For productivity you can add a shortcut to these operators with left click over the button > Add shortcut


<!--
## Todo:
- performance upgrade via stroke proximity checking with a kdtree 
- authorize snapping on the same layer as an option
-  -->

---

## Changelog:

2.1.0

- feat: magnet in 3D space to fit underline fills to line (experimental Alpha)
- fix: Compatibility with blender 3.3+

2.0.1:

- UI: changed panel name
- doc: youtube link

2.0.0:
- performance: deleted old _sticky_ condition from V1
- feat: new filter to target only target nearby  upper or lower layers
- UI: choice to display the point
- code: cleanup
- doc: big readme update

1.9.0:

- feat: new operator to magnet once without modal control
- UI: better arrangement
- fix: bug when resizing brush

1.8.0:

- feat: Option to display ghost points (draw virtual point position on screen)
- feat: brush resize:
    - resize brush with `F`
    - resize magnet influence with `shift + F`
- code: refactor
- UX: exposing only brush magnet, not global magnet

1.7.0

- performance: only target strokes visible on screen
- fix: big bug on basic magnet pen drag introduced in last version
- display radius of magnet proximity on mouse (though it's a radius that center should be "per points")
- fix: pen radius display

1.6.0

- Change: move global magnet by clicking, (Better global magnet control than previous "grab")

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