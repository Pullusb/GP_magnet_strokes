bl_info = {
    "name": "GP magnet strokes",
    "description": "Magnet a fill stroke on a line with designated material",
    "author": "Samuel Bernou",
    "version": (3, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D",
    "warning": "Still experimental",
    "doc_url": "https://github.com/Pullusb/GP_magnet_strokes",
    "tracker_url": "https://github.com/Pullusb/GP_magnet_strokes/issues",
    "category": "Object" }

from . import brush_magnet
from . import basic_magnet
from . import ops_magnet
from . import magnet_3d

import bpy


class GPMGT_PT_magnet_panel(bpy.types.Panel):
    bl_label = "Magnet Strokes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gpencil"

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        layout.prop(context.scene.gp_magnetools, 'mgnt_near_layers_targets')
        layout.prop(context.scene.gp_magnetools, 'mgnt_material_targets')
        layout.prop(context.scene.gp_magnetools, 'mgnt_target_line_only')
        layout.prop(context.scene.gp_magnetools, 'mgnt_select_mask')
        layout.prop(context.scene.gp_magnetools, 'mgnt_snap_to_points')
        layout.prop(context.scene.gp_magnetools, 'mgnt_display_ghosts')

        # layout.operator('gp.magnet_lines', text='Magnet lines', icon='SNAP_ON')
        ## call through 

        row = layout.row()
        row.prop(context.scene.gp_magnetools, 'mgnt_radius', text='Brush Size')
        row.prop(context.scene.gp_magnetools, 'mgnt_tolerance')# text='Magnet radius'
        row = layout.row()
        row.operator('gpencil.magnet_brush', text='Magnet Brush', icon='SNAP_ON')
        row.operator('gp.magnet_lines_all', text='Magnet', icon='SNAP_ON')

class GPMGT_PT_magnet_3d_panel(bpy.types.Panel):
    bl_label = "Experimental: Magnet 3D Distance"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gpencil"
    bl_parent_id = 'GPMGT_PT_magnet_panel'
    # bl_options = {'DEFAULT_CLOSED'}t

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True

        # layout.prop(context.scene.gp_magnetools, 'mgnt_3d_distance')
        # layout.prop(context.scene.gp_magnetools, 'mgnt_3d_snap_under_line')

        layout.prop(context.scene.gp_magnetools, 'mgnt_3d_layer_prefix_filter')
        layout.prop(context.scene.gp_magnetools, 'mgnt_3d_under_line_margin')

        layout.operator('gp.magnet_by_3d_distance', text='Magnet 3D', icon='SNAP_ON')
        
        layout.separator()
        layout.operator('gp.test_radius', text='Radius Test Spheres', icon='META_BALL')

class MGNT_PGT_settings(bpy.types.PropertyGroup) :
    mgnt_near_layers_targets : bpy.props.IntProperty(
        name="Near Layers Target",
        description="Layers to target near active layer in stack\n(0 = all, 2 = two layers above, -1 = one layer below)\nBig values allow to target all above or all below",
        default=100, soft_min=-2000, soft_max=2000, step=1, options={'HIDDEN'})

    mgnt_material_targets : bpy.props.StringProperty(
        name="Materials", 
        description="Filter list of targeted materials for the magnet (coma separated names, not case sensitive)\n(e.g: 'line,Solid Black,fx')\nLeave empty to target all lines", default="")# update=None, get=None, set=None
    
    mgnt_select_mask : bpy.props.BoolProperty(
        name="Magnet on selection", 
        description="Snap only on selected lines (Drastically improve performances by reducing target to evaluate)", default=False, options={'HIDDEN'})#options={'ANIMATABLE'},subtype='NONE', update=None, get=None, set=None

    mgnt_target_line_only : bpy.props.BoolProperty(
        name="Target line only", 
        description="Avoid line that have a Fill material", 
        default=True, options={'HIDDEN'})#options={'ANIMATABLE'},subtype='NONE', update=None, get=None, set=None
    
    mgnt_snap_to_points : bpy.props.BoolProperty(
        name="Snap to points", 
        description="Snap on points instead of lines (Better performance)", 
        default=False, options={'HIDDEN'})#options={'ANIMATABLE'},subtype='NONE', update=None, get=None, set=None

    mgnt_tolerance : bpy.props.IntProperty(
        name="Magnet Distance", 
        description="Area of effect of the magnet (radius around point in pixel value)", 
        default=100, min=1, max=2**31-1, soft_min=1, soft_max=2**31-1, step=1, subtype='PIXEL', options={'HIDDEN'})
    
    mgnt_radius : bpy.props.IntProperty(name="Radius", 
    description="Radius of the brush\nUse [/], X/C, numpad -/+ or mousewheel down/up to modify during draw", 
    default=50, min=1, max=500, soft_min=0, soft_max=300, step=1)#, options={'HIDDEN'}#subtype = 'PIXEL' ?

    mgnt_display_ghosts : bpy.props.BoolProperty(
        name="Display Position", 
        description="Show the point position before magnet is applied to help repositionning", default=True, options={'HIDDEN'})

    ## 3D distances

    mgnt_3d_distance : bpy.props.FloatProperty(
        name="Magnet 3D Distance",
        description="Area of effect of the magnet (radius around point in blender unit value)",
        default=0.01, options={'HIDDEN'})
    
    mgnt_3d_snap_under_line : bpy.props.BoolProperty(
        name="Points Under Range", 
        description="Avoid line that have a Fill material", 
        default=True, options={'HIDDEN'})
    
    mgnt_3d_under_line_margin : bpy.props.FloatProperty(
        name="Line Virtual Margin",
        description="add a margin to the line (as a percentage value)",
        default=0, min=-100, soft_max=100, subtype='PERCENTAGE', options={'HIDDEN'})
    
    mgnt_3d_layer_prefix_filter : bpy.props.StringProperty(
        name="Only prefixes",
        default='CO_,',
        description="Only magnet layers with prefix", options={'HIDDEN'})



addon_keymaps = []
def register_keymaps():
    addon = bpy.context.window_manager.keyconfigs.addon
    # km = addon.keymaps.new(name = "3D View", space_type = "VIEW_3D")
    ### keymap itemps detail
    # kmi = km.keymap_items.new(
    #     name="Magnet fill",
    #     idname="gp.magnet_lines",
    #     type="F",
    #     value="PRESS",
    #     shift=True,
    #     ctrl=True,
    #     alt = False,
    #     oskey=False
    #     )

    km = addon.keymaps.new(name = "Grease Pencil", space_type = "EMPTY", region_type='WINDOW')
    kmi = km.keymap_items.new('gpencil.magnet_brush', type='F5', value='PRESS')
    addon_keymaps.append((km, kmi))
    

def unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

### --- REGISTER ---

classes=(
MGNT_PGT_settings,
GPMGT_PT_magnet_panel,
GPMGT_PT_magnet_3d_panel,
)

def register():
    brush_magnet.register()
    basic_magnet.register()
    ops_magnet.register()
    magnet_3d.register()
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # if not bpy.app.background:
    # register_keymaps()# testing keymap
    bpy.types.Scene.gp_magnetools = bpy.props.PointerProperty(type = MGNT_PGT_settings)

def unregister():
    # if not bpy.app.background:
    # unregister_keymaps()# testing keymap
    brush_magnet.unregister()
    basic_magnet.unregister()
    ops_magnet.unregister()
    magnet_3d.unregister()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gp_magnetools

if __name__ == "__main__":
    register()