bl_info = {
    "name": "GP magnet strokes",
    "description": "Magnet a fill stroke on a line with designated material",
    "author": "Samuel Bernou",
    "version": (1, 9, 0),
    "blender": (2, 83, 0),
    "location": "View3D",
    "warning": "Still in development",
    "doc_url": "https://github.com/Pullusb/GP_magnet_strokes",
    "category": "Object" }

from . import brush_magnet
from . import basic_magnet
from . import ops_magnet

import bpy


class GPMGT_PT_magnet_panel(bpy.types.Panel):
    bl_label = "Magnet line"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gpencil"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.gp_magnetools, 'mgnt_material_targets')
        layout.prop(context.scene.gp_magnetools, 'mgnt_target_line_only')
        layout.prop(context.scene.gp_magnetools, 'mgnt_select_mask')
        layout.prop(context.scene.gp_magnetools, 'mgnt_snap_to_points')

        # layout.operator('gp.magnet_lines', text='Magnet lines', icon='SNAP_ON')
        ## call through 

        row = layout.row()
        row.prop(context.scene.gp_magnetools, 'mgnt_radius', text='Brush Size')
        row.prop(context.scene.gp_magnetools, 'mgnt_tolerance')# text='Magnet radius'
        row = layout.row()
        row.operator('gp.magnet_brush', text='Magnet Brush', icon='SNAP_ON')
        row.operator('gp.magnet_lines_all', text='Magnet', icon='SNAP_ON')

class MGNT_PGT_settings(bpy.types.PropertyGroup) :
    mgnt_material_targets : bpy.props.StringProperty(
        name="Materials", description="Filter list of targeted materials for the magnet (coma separated names, not case sensitive)\n(e.g: 'line,Solid Black,fx')\nLeave empty to target all lines", default="")# update=None, get=None, set=None
    
    mgnt_select_mask : bpy.props.BoolProperty(
        name="Magnet on selection", description="Snap only on selected lines (Drastically improve performances by reducing target to evaluate)", default=False, options={'HIDDEN'})#options={'ANIMATABLE'},subtype='NONE', update=None, get=None, set=None

    mgnt_target_line_only : bpy.props.BoolProperty(
        name="Target line only", description="Avoid line that have a Fill material", default=True, options={'HIDDEN'})#options={'ANIMATABLE'},subtype='NONE', update=None, get=None, set=None
    
    mgnt_snap_to_points : bpy.props.BoolProperty(
        name="Snap to points", description="Snap on points instead of lines (Better performance)", default=False, options={'HIDDEN'})#options={'ANIMATABLE'},subtype='NONE', update=None, get=None, set=None

    mgnt_tolerance : bpy.props.IntProperty(
        name="Magnet Distance", description="Area of effect of the magnet (radius around point in pixel value)", default=25, min=1, max=2**31-1, soft_min=1, soft_max=2**31-1, step=1, subtype='PIXEL', options={'HIDDEN'})
    
    mgnt_radius : bpy.props.IntProperty(name="Radius", 
    description="Radius of the brush\nUse [/], X/C, numpad -/+ or mousewheel down/up to modify during draw", 
    default=20, min=1, max=500, soft_min=0, soft_max=300, step=1)#, options={'HIDDEN'}#subtype = 'PIXEL' ?


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
    km.keymap_items.new('gp.magnet_brush', type='F5', value='PRESS')
    addon_keymaps.append(km)
    


def unregister_keymaps():
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        for kmi in km.keymap_items:
            km.keymap_items.remove(kmi)
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

### --- REGISTER ---

classes=(
MGNT_PGT_settings,
GPMGT_PT_magnet_panel,
)

def register():
    brush_magnet.register()
    basic_magnet.register()
    ops_magnet.register()
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # if not bpy.app.background:
    register_keymaps()
    bpy.types.Scene.gp_magnetools = bpy.props.PointerProperty(type = MGNT_PGT_settings)

def unregister():
    # if not bpy.app.background:
    unregister_keymaps()
    brush_magnet.unregister()
    basic_magnet.unregister()
    ops_magnet.unregister()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gp_magnetools

if __name__ == "__main__":
    register()