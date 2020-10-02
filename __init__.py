bl_info = {
    "name": "GP magnet strokes",
    "description": "Magnet a fill stroke on a line with designated material",
    "author": "Samuel Bernou",
    "version": (1, 3, 0),
    "blender": (2, 83, 0),
    "location": "View3D",
    "warning": "This an early alpha, still in development",
    "doc_url": "https://github.com/Pullusb/GP_magnet_strokes",
    "category": "Object" }


import bpy, os
import numpy as np
import mathutils
from mathutils import Vector
from math import sqrt
from sys import platform
import subprocess
from time import time#Dbg-time

## modal import
import gpu
import bgl
import blf
from gpu_extras.batch import batch_for_shader


def get_last_index(context=None):
    if not context:
        context = bpy.context
    return 0 if context.tool_settings.use_gpencil_draw_onback else -1

# -----------------
### Vector utils 2d
# -----------------

def location_to_region(worldcoords):
    from bpy_extras import view3d_utils
    return view3d_utils.location_3d_to_region_2d(bpy.context.region, bpy.context.space_data.region_3d, worldcoords)

def region_to_location(viewcoords, depthcoords):
    from bpy_extras import view3d_utils
    return view3d_utils.region_2d_to_location_3d(bpy.context.region, bpy.context.space_data.region_3d, viewcoords, depthcoords)

# unused
def single_vector_length_2d(v):
    return sqrt((v[0] * v[0]) + (v[1] * v[1]))

def vector_length_2d(A,B):
    ''''take two Vector and return length'''
    return sqrt((A[0] - B[0])**2 + (A[1] - B[1])**2)

# unused
def closest_point_on_line_next_to_point(p1, p2, p3):
    '''return closest point to p3 on the segement represented by p1-p2 '''
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    dx, dy = x2-x1, y2-y1
    det = dx*dx + dy*dy
    a = (dy*(y3-y1)+dx*(x3-x1))/det
    return x1+a*dx, y1+a*dy

def get_gp_draw_plane(context):
    ''' return tuple with plane coordinate and normal
    of the curent drawing accordign to geometry'''

    settings = context.scene.tool_settings
    orient = settings.gpencil_sculpt.lock_axis# 'VIEW', 'AXIS_Y', 'AXIS_X', 'AXIS_Z', 'CURSOR'
    loc = settings.gpencil_stroke_placement_view3d# 'ORIGIN', 'CURSOR', 'SURFACE', 'STROKE'
    mat = context.object.matrix_world if context.object else None
    # -> placement
    if loc == "CURSOR":
        plane_co = context.scene.cursor.location
    else:#ORIGIN (also on origin if set to 'SURFACE', 'STROKE')
        if not context.object:
            plane_co = None
        else:
            plane_co = context.object.matrix_world.to_translation()# context.object.location


    # -> orientation
    if orient == 'VIEW':
        plane_no = context.space_data.region_3d.view_rotation @ Vector((0,0,1))
        ## create vector, then rotate by view quaternion
        # plane_no = Vector((0,0,1))
        # plane_no.rotate(context.space_data.region_3d.view_rotation)
        
        ## only depth is important, can return None so region to location use same depth
        # plane_no = None


    elif orient == 'AXIS_Y':#front (X-Z)
        plane_no = Vector((0,1,0))
        plane_no.rotate(mat)

    elif orient == 'AXIS_X':#side (Y-Z)
        plane_no = Vector((1,0,0))
        plane_no.rotate(mat)

    elif orient == 'AXIS_Z':#top (X-Y)
        plane_no = Vector((0,0,1))
        plane_no.rotate(mat)

    elif orient == 'CURSOR':
        plane_no = Vector((0,0,1))
        plane_no.rotate(context.scene.cursor.matrix)
    
    return plane_co, plane_no

## TODO
### use points only ( brute force or with a kd_tree) ?
# test a mode with points only (need to fuse overlapping strokes (if those are adjacent strokes ?))
# Test in a modal operator, use a draw handler to show initial position to target position (As debug tool...)



### ---- Modal operator


# Simple exemple of event keypress handling and basic draw in modal ops with detection of ctrl/alt/shift modifiers
# from gpu_extras.presets import draw_circle_2d
"""
def draw_callback_px(self, context):
    '''Draw callback use by modal to draw in viewport'''
    ## lines and shaders
    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')#initiate shader
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(2)

    # Draw line showing mouse path
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": self.mouse_path})
    shader.bind()
    shader.uniform_float("color", (0.5, 0.5, 0.5, 0.5))#grey-light
    batch.draw(shader)

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)

    ## text
    font_id = 0

    ## Show active modifier key (not necessary if you need performance)
    if self.pressed_alt or self.pressed_shift or self.pressed_ctrl:
        # print(f'mods: alt {self.pressed_alt} - shift {self.pressed_shift} - ctrl {self.pressed_ctrl}')
        blf.position(font_id, self.mouse[0]+10, self.mouse[1]+10, 0)
        blf.size(font_id, 30, 72)#Id, Point size of the font, dots per inch value to use for drawing.
        if self.pressed_alt and self.pressed_shift:
            blf.draw(font_id, 'x')
        elif self.pressed_alt:
            blf.draw(font_id, '-')
        elif self.pressed_shift:
            blf.draw(font_id, '+')
        elif self.pressed_ctrl:
            blf.draw(font_id, 'o')

    ## Draw text debug infos
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, f'Infos - mouse coord: {self.mouse} - mouse_steps: {len(self.mouse_path)}')

"""

class GPMGT_OT_magnet_gp_lines(bpy.types.Operator):
    """Magnet fill strokes to line stroke"""
    bl_idname = "gp.magnet_lines"
    bl_label = "Magnet gp lines"
    bl_description = "Try to magnet grease pencil stroke to closest stroke in other layers"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'GPENCIL'

    pressed_key = 'NOTHING'

    def compute_magnet(self, context):
        '''Basic magnet (slightly faster cause less condition)'''

        for j, mp in enumerate(self.pos_2d):
            prevdist = 10000
            res = None

            for stroke_pts in self.target_strokes:
                for i in range(len(stroke_pts)-1):
                    pos, percentage = mathutils.geometry.intersect_point_line(mp, stroke_pts[i], stroke_pts[i+1])

                    if percentage <= 0:#head
                        pos = stroke_pts[i]
                    elif 1 <= percentage:#tail
                        pos = stroke_pts[i+1]

                    ## check distance against previous
                    dist = vector_length_2d(pos, mp)
                    if dist < prevdist:
                        res = pos
                        prevdist = dist

            self.mv_points[j].co = self.matworld.inverted() @ region_to_location(res, self.depth)

    def compute_proximity_magnet(self, context):
        # self.target_strokes # list of pointlists 2d [[p,p][p,p,p]]
        # self.mv_points # list of moving point 2d [p,p,p] 
        # self.org_pos # list of original pos (3d)
        # self.pos_2d # list of last registered 2d pos

        for j, mp in enumerate(self.pos_2d):
            #reset
            prevdist = 10000
            res = None
            
            # search closest
            for stroke_pts in self.target_strokes:
                for i in range(len(stroke_pts)-1):
                    pos, percentage = mathutils.geometry.intersect_point_line(mp, stroke_pts[i], stroke_pts[i+1])

                    if percentage <= 0:#head
                        pos = stroke_pts[i]
                    elif 1 <= percentage:#tail
                        pos = stroke_pts[i+1]

                    ## check distance against previous
                    dist = vector_length_2d(pos, mp)
                    if dist < prevdist:
                        res = pos
                        prevdist = dist

            ## Use a proximity a snap with tolerance:
            if prevdist <= self.tolerance:
                #res is 2d, need 3d coord
                self.mv_points[j].co = self.matworld.inverted() @ region_to_location(res, self.depth)
            else:
                self.mv_points[j].co = self.matworld.inverted() @ region_to_location(mp, self.depth)


    def compute_proximity_sticky_magnet(self, context, stick=False):
        '''Sticky version that lock the points magneted once'''
        for j, mp in enumerate(self.pos_2d):
            prevdist = 10000
            res = None
            
            for stroke_pts in self.target_strokes:
                for i in range(len(stroke_pts)-1):
                    pos, percentage = mathutils.geometry.intersect_point_line(mp, stroke_pts[i], stroke_pts[i+1])

                    if percentage <= 0:#head
                        pos = stroke_pts[i]
                    elif 1 <= percentage:#tail
                        pos = stroke_pts[i+1]

                    ## check distance against previous
                    dist = vector_length_2d(pos, mp)
                    if dist < prevdist:
                        res = pos
                        prevdist = dist

            if self.sticked[j]: # use sticked coord
                self.mv_points[j].co = self.sticked[j]

            elif prevdist <= self.tolerance:# magnet
                self.mv_points[j].co = self.matworld.inverted() @ region_to_location(res, self.depth)# res is 2d, need 3d coord
                if stick: #via event.ctrl
                    self.sticked[j] = self.matworld.inverted() @ region_to_location(res, self.depth)

            else:# keep following cursor
                self.mv_points[j].co = self.matworld.inverted() @ region_to_location(mp, self.depth)

    def compute_point_proximity_sticky_magnet(self, context, stick=False):
        '''Sticky version to point directly'''
        for j, mp in enumerate(self.pos_2d):
            prevdist = 10000
            res = None
            
            for stroke_pts in self.target_strokes:
                for i, pos in enumerate(stroke_pts):
                    ## check distance against previous
                    dist = vector_length_2d(pos, mp)
                    if dist < prevdist:
                        res = pos
                        prevdist = dist

            if self.sticked[j]: # use sticked coord
                self.mv_points[j].co = self.sticked[j]

            elif prevdist <= self.tolerance:# magnet
                self.mv_points[j].co = self.matworld.inverted() @ region_to_location(res, self.depth)# res is 2d, need 3d coord
                if stick: #via event.ctrl
                    self.sticked[j] = self.matworld.inverted() @ region_to_location(res, self.depth)

            else:# keep following cursor
                self.mv_points[j].co = self.matworld.inverted() @ region_to_location(mp, self.depth)

    def autoclean(self, context):
        ct = 0
        # passed_coords = [] # here means point overlap check across strokes...
        for s in reversed([s for s in context.object.data.layers.active.active_frame.strokes if s.select]):
            passed_coords = []# per stroke analysis
            double_list = []
            for i, p in enumerate(s.points):
                if not p.select or not p in self.mv_points:
                    continue
                if p.co in passed_coords:
                    double_list.append(i)
                    continue
                passed_coords.append(p.co)
                        
            for i in reversed(double_list):
                s.points.pop(index=i)
            ct += len(double_list)
        
        if ct:
            print(f'Deleted {ct} overlapping points')

    def modal(self, context, event):
        # context.area.tag_redraw()

        ### /TESTER - keycode printer (flood console but usefull to know a keycode name)
        # if event.type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:#avoid flood of mouse move.
            # print('key:', event.type, 'value:', event.value)
        ###  TESTER/


        ## Get mouse move
        if event.type in {'MOUSEMOVE'}:
            # INBETWEEN_MOUSEMOVE : Mouse sub-moves when too fast and need precision to get higher resolution sample in coordinate.
            ## update by mouse moves ! 
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            ms_delta = Vector((self.mouse[0] - self.initial_ms[0], self.mouse[1] - self.initial_ms[1]))
            self.pos_2d = [pos + ms_delta for pos in self.initial_pos_2d]

            # self.compute_proximity_magnet(context)# on line
            if self.point_snap:
                self.compute_point_proximity_sticky_magnet(context, stick=event.ctrl)# on point with stickyness ctrl 
            else:
                self.compute_proximity_sticky_magnet(context, stick=event.ctrl)# on line with stickiness ctrl
            
            # ## Store mouse position in a variable
            
            # ## Store mouse path in a list (only if left click is pressed)
            # if self.pressed_key == 'LEFTMOUSE':# This is evaluated as a continuous press
            #     # self.mouse_path.append((event.mouse_region_x, event.mouse_region_y))
            #     pass

        '''
        ### /CONTINUOUS PRESS
        if event.type == 'LEFTMOUSE':
            self.pressed_key = 'LEFTMOUSE'
            ## While pushed, variable pressed stay on
            
            if event.value == 'RELEASE':
                # print('Action on release')#Dbg

                #if release, stop continuous press and do the thing !
                # Reset the key
                self.pressed_key = 'NOTHING'
                
                ## if needed, add UNDO STEP push before doing the clicked action (usefull for drawing strokes)
                # bpy.ops.ed.undo_push()

                # if skip_condition :
                #     self.pressed_key = 'NOTHING'# reset pressed_key state
                #     return {'RUNNING_MODAL'}

                # if stop_condition:
                #     # self.report({'ERROR'}, 'Error message for you, dear user')
                #     return {'CANCELLED'}

                ## Do things according to modifier detected (on release here) Put combo longest key combo first
        

        if self.pressed_key == 'LEFTMOUSE':# using pressed_key variable
            ## Code here is continuously triggered during press
            pass
        ### CONTINUOUS PRESS/


        ## /SINGLE PRESS
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self.pressed_ctrl:
                print('Ctrl + click')
            else:
                print('Click')
            ## Can also finish on click (better do a dedicated exit func if duplicated with abort code)
            # bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            # return {'FINISHED'}
        ## SINGLE PRESS/
        '''


        ### KEYBOARD SINGLE PRESS

        if event.type in {'NUMPAD_MINUS', 'LEFT_BRACKET', 'WHEELDOWNMOUSE'}:
            if event.value == 'PRESS':
                self.tolerance -= 1
                if self.tolerance <=1:#clamp to 1
                    self.tolerance = 1
                context.scene.gp_magnetools.mgnt_tolerance = self.tolerance
                context.area.tag_redraw()

        if event.type in {'NUMPAD_PLUS', 'RIGHT_BRACKET', 'WHEELUPMOUSE'}:
            if event.value == 'PRESS':
                self.tolerance += 1
                context.scene.gp_magnetools.mgnt_tolerance = self.tolerance
                context.area.tag_redraw()

        # Valid
        if event.type in {'RET', 'SPACE', 'LEFTMOUSE'}:
            self.stop_modal(context)
            
            ## depth correction
            
            for i, p in enumerate(self.mv_points):
                ## 1-> reattribute original depth (Pretty much always bad since point has translated in persp... return jaggy lines)
                # p.co = self.matworld.inverted() @ region_to_location( location_to_region(self.matworld @ p.co), self.matworld @ self.org_pos[i] )# use org loc as depth
                
                ## 2-> use raycast on old points (must be bad too...) ## intersect_line_plane(line_a, line_b, plane_co, plane_no, no_flip=False) 
                # plane_no = self.matworld @ p.co - slef.view_co
                # p.co = mathutils.geometry.intersect_line_plane(slef.view_co, self.matworld @ p.co, self.matworld @ self.org_pos[i], plane_no)#, no_flip=False

                ## 3-> raycast on drawplane
                p.co = self.matworld.inverted() @ mathutils.geometry.intersect_line_plane(self.view_co, self.matworld @ p.co, self.plane_co, self.plane_no)

            ## autoclean overlapping vertices
            ## ugly method
            self.autoclean(context)

            self.report({'INFO'}, "Magnet applyed")
            return {'FINISHED'}
        
        # Abort
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.stop_modal(context)
            for i, p in enumerate(self.mv_points):
                p.co = self.org_pos[i]
            self.report({'WARNING'}, "Cancelled")
            return {'CANCELLED'}

        ## TIMER
        # if event.type == 'TIMER':
        #     print('tick')

        return {'RUNNING_MODAL'}

    def stop_modal(self, context):
        context.area.header_text_set(None)
        ## Remove timer (if there was any)
        # context.window_manager.event_timer_remove(self.draw_event)
        
        ## Remove draw handler (if there was any)
        # bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')


    def invoke(self, context, event):
        ## stop if not in perspective view
        if not context.area.spaces[0].region_3d.is_perspective:
            self.report({'ERROR'}, "You are in Orthographic view ! (generate imprecision)\n(press 5 on your numpad to toggle perspective view)")
            return {'CANCELLED'}

        self.report({'INFO'}, "Magnet On")
        settings = context.scene.gp_magnetools

        ## rules
        self.tolerance = settings.mgnt_tolerance
        self.point_snap = settings.mgnt_snap_to_points
        select_mask = settings.mgnt_select_mask
        target_line_only = settings.mgnt_target_line_only
        #source_fill_only = False

        ## initialise
        start_init = time()#Dbg-time
        

        ## resample on the fly - BUT select all the line... (kill selection) add it as separate.
        # bpy.ops.gpencil.stroke_sample(length=0.04)


        ## get projection plane (to reproject upon confirm)
        self.view_co = context.space_data.region_3d.view_matrix.inverted().translation
        self.plane_co, self.plane_no = get_gp_draw_plane(context)
        
        ## get material to target (with selection switch if needed)
        material_targets = [name.lower().strip(' ,') for name in settings.mgnt_material_targets.split(',')]
        while "" in material_targets :
            material_targets.remove("") 
        
        mat_ids = []

        ob = context.object
        materials = ob.data.materials
        for i, m in enumerate(materials):
            if m.name.lower() in material_targets:
                mat_ids.append(i)

        if material_targets and not mat_ids:# No target found
            self.report({'ERROR'}, f"No material target found from in list {settings.mgnt_material_targets} (analysed as {'|'.join(material_targets)})\nChange targets names or leave field empty to target all materials")
            return {'CANCELLED'}
        
        # self.target_points = []
        # self.target_2d_co = []
        self.matworld = ob.matrix_world
        gpl = ob.data.layers

        ## avoid hided layers and avoid active layer (fill layer)...
        tgt_layers = [l for l in gpl if not l.hide and l != gpl.active]
        # all_strokes = [s for l in tgt_layers for s in l.active_frame.strokes if s.material_index in mat_ids]
        # self.target_strokes = [[(p, location_to_region(self.matworld @ p.co)) for p in s.points] for s in all_strokes]
        
        ## Get all 2D point position of targeted lines
        self.target_strokes = []
        for l in tgt_layers:            
            for s in l.active_frame.strokes:
                
                ## filter on specific material target
                ## pass if no material targets defined
                if mat_ids and not s.material_index in mat_ids:
                    continue
                
                ## Get all type except fills
                if target_line_only and materials[s.material_index].grease_pencil.show_fill:
                    continue
                
                ## work only on selected strokes from other layers (usefull to magnet on specific strokes)
                if select_mask and not s.select:
                    continue

                self.target_strokes.append([location_to_region(self.matworld @ p.co) for p in s.points])

                
                ##### POINT MODE: All mixed points pairs (valid for direct point search, dont take strokes gap for line search) 
                # for p in s.points:
                #     self.target_points.append(p)
                #     self.target_2d_co.append(location_to_region(self.matworld @ p.co))
       

        # print(f'End target line infos get: {time() - start_init:.4f}s')#Dbg-time
        if not self.target_strokes:
            self.report({'ERROR'}, "No target strokes found")
            return {'CANCELLED'}

        ## store moving points
        self.mv_points = []
        # Work on last stroke hwne in paint mode
        if context.mode == 'PAINT_GPENCIL':
            self.mv_points = [p for p in gpl.active.active_frame.strokes[get_last_index(context)].points]
        else:
            org_strokes = [s for s in gpl.active.active_frame.strokes if s.select]

            for s in org_strokes:
                ## source stroke filter
                # if source_fill_only and not materials[s.material_index].grease_pencil.show_fill:# negative authorize double (fill + line)
                #     continue
                for p in s.points:
                    if not p.select:
                        continue
                    self.mv_points.append(p)

        ## error handling
        if not self.mv_points:
            self.report({'ERROR'}, "No points to move found")
            return {'CANCELLED'}

        ## store initial position of moving_strokes
        self.org_pos = [Vector(p.co[:]) for p in self.mv_points]## need a copy (or [:]) !!! else it follow point coordinate as it changes !
        self.pos_2d = [location_to_region(self.matworld @ p.co) for p in self.mv_points]

        self.initial_pos_2d = self.pos_2d.copy()
        
        self.sticked = [False]*len(self.pos_2d)

        # use depth of first point to reproject on this depth
        self.depth = self.org_pos[0]
        print(f'Magnet init: {time() - start_init:.4f}s')#Dbg-time

        ## Add the region OpenGL drawing callback (only if drawing is needed)
        ## draw in view space with 'POST_VIEW' and 'PRE_VIEW'
        # args = (self, context)
        # self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        
        ## If a timer is needed during modal
        # self.draw_event = context.window_manager.event_timer_add(0.1, window=context.window)#Interval in seconds
        
        ## initiate variable to use (ex: mouse coords)
        self.mouse = (0, 0) # updated tuple of mouse coordinate
        self.initial_ms = (event.mouse_region_x, event.mouse_region_y)
        
        ## Starts the modal
        display_text = 'Magnet mode | Valid: Left Clic, Space, Enter | Cancel: Right Clic, Escape |'
        if material_targets and mat_ids:
            display_text += f' Target materials: "{"|".join(material_targets)}"'

        context.area.header_text_set(display_text)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


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
        layout.prop(context.scene.gp_magnetools, 'mgnt_tolerance')

        layout.operator('gp.magnet_lines', text='Magnet lines', icon='SNAP_ON')

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
        name="Magnet Distance", description="Area of effect of the magnet (radius around point in pixel value)", default=10, min=1, max=2**31-1, soft_min=1, soft_max=2**31-1, step=1, subtype='PIXEL', options={'HIDDEN'})

addon_keymaps = []
def register_keymaps():
    addon = bpy.context.window_manager.keyconfigs.addon
    # km = addon.keymaps.new(name = "3D View", space_type = "VIEW_3D")
    km = addon.keymaps.new(name = "Grease Pencil", space_type = "EMPTY", region_type='WINDOW')
    
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
    km.keymap_items.new('gp.magnet_lines', type='F5', value='PRESS')


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
GPMGT_OT_magnet_gp_lines,
GPMGT_PT_magnet_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # if not bpy.app.background:
    register_keymaps()
    bpy.types.Scene.gp_magnetools = bpy.props.PointerProperty(type = MGNT_PGT_settings)

def unregister():
    # if not bpy.app.background:
    unregister_keymaps()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gp_magnetools

if __name__ == "__main__":
    register()