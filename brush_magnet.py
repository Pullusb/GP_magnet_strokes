from .__init__ import *

import bpy
from mathutils import Vector, Matrix
from mathutils import geometry
import math
from math import sqrt

import numpy as np
import gpu
import bgl
import blf

from time import time
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_circle_2d


def circle_2d(coord, r, num_segments):
    '''create circle, ref: http://slabode.exofire.net/circle_draw.shtml'''
    cx, cy = coord
    points = []
    theta = 2 * 3.1415926 / num_segments
    c = math.cos(theta) #precalculate the sine and cosine
    s = math.sin(theta)
    x = r # we start at angle = 0
    y = 0
    for i in range(num_segments):
        #bgl.glVertex2f(x + cx, y + cy) # output vertex
        points.append((x + cx, y + cy))
        # apply the rotation matrix
        t = x
        x = c * x - s * y
        y = s * t + c * y

    return points

def draw_callback_px(self, context):
    scn = context.scene
    full_radius = scn.gp_magnetools.mgnt_radius
    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(2)

    # paint
    """
    batch = batch_for_shader(shader, 'TRIS', {"pos": self.vertices}, indices=self.indices)
    shader.bind()
    shader.uniform_float("color", self.paint_color)#indigo (0, 0.5, 0.5, 1.0)
    batch.draw(shader)
    """

    '''
    #draw debug line showing mouse path
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": self.mouse_path})
    shader.bind()
    shader.uniform_float("color", (0.5, 0.5, 0.5, 0.5))#grey-light
    batch.draw(shader)
    '''

    #paint widget
    #paint_widget = Point(self.mouse).buffer(scn.GPS_radius, 2)#shapely mode !
    
    paint_widget = circle_2d(self.mouse, self.pen_radius, self.crosshair_resolution)#optimisation ?
    paint_widget.append(paint_widget[0])#re-insert last coord to close the circle

    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": paint_widget})
    shader.bind()
    shader.uniform_float("color", (0.6, 0.0, 0.0, 0.5))#red-light
    batch.draw(shader)

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)

    ## text
    font_id = 0

    ## show active modifier
    # if self.pressed_alt or self.pressed_shift:
    #     blf.position(font_id, self.mouse[0]+full_radius, self.mouse[1]+full_radius, 0)
    #     blf.size(font_id, 15, 72)
    #     if self.pressed_alt:
    #         blf.draw(font_id, '-')
    #     else:
    #         blf.draw(font_id, '+')

    ## draw text debug infos
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, f'Magnet Brush - radius: {full_radius}')

class GPMGT_OT_magnet_brush(bpy.types.Operator):
    """Magnet fill strokes to line stroke with a brush"""
    bl_idname = "gp.magnet_brush"
    bl_label = "Magnet Brush"
    bl_description = "Try to magnet grease pencil stroke to closest stroke in other layers"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'GPENCIL'

    pressed_key = 'NOTHING'

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
        context.area.tag_redraw()

        ### /TESTER - keycode printer (flood console but usefull to know a keycode name)
        # if event.type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:#avoid flood of mouse move.
            # print('key:', event.type, 'value:', event.value)
        ###  TESTER/

        #handle the continuous press
        if event.type == 'LEFTMOUSE' :
            # if event.value == 'PRESS':
            self.pressed_key = 'LEFTMOUSE'
            #while pushed, variable pressed stay on...
            if event.value == 'RELEASE':
                #if release, stop and do the thing !
                self.pressed_key = 'NOTHING'
                #reset mouse prev to avoid jump in hyper space of the points
                self.mouse_prev = None

        ## Get mouse move
        if event.type in {'MOUSEMOVE'}:
            self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            # INBETWEEN_MOUSEMOVE : Mouse sub-moves when too fast and need precision to get higher resolution sample in coordinate.
            ## update by mouse moves !
            if self.pressed_key == 'LEFTMOUSE':
                if not self.mouse_prev:
                    self.mouse_prev = self.mouse
                    self.radius_prev = self.pen_radius
                
                else:
                    self.pen_radius = int(context.scene.gp_magnetools.mgnt_radius * event.pressure)
                    #debug pressure
                    # print('pression', event.pressure, '-> self.pen_radius: ', self.pen_radius)

                    if self.pen_radius < 1:
                        self.pen_radius = 1
                    ## Permanent move from initial position
                    # ms_delta = Vector((self.mouse[0] - self.initial_ms[0], self.mouse[1] - self.initial_ms[1]))
                    # self.pos_2d = [pos + ms_delta for pos in self.initial_pos_2d]

                    ## updating position if points are taken inside radius
                    ms_delta = Vector((self.mouse[0] - self.mouse_prev[0], self.mouse[1] - self.mouse_prev[1]))
                    
                    ## bring points if they are in the radius of the coordsmouse
                    for i, pos in enumerate(self.pos_2d):
                        if (pos - self.mouse_prev).length > self.radius_prev:
                            continue
                        # TODO Check if possiblea to make a falloff (linear to start)
                        # with percentage of the length to max as a reduction to mouse delta (will slowdown stuff...)
                        self.pos_2d[i] = pos + ms_delta
                    
                    ## store prev for next action
                    self.mouse_prev = self.mouse
                    self.radius_prev = self.pen_radius
                    
                    # self.compute_proximity_magnet(context)# on line
                    if self.point_snap:
                        self.compute_point_proximity_sticky_magnet(context, stick=event.ctrl)# on point with stickyness ctrl 
                    else:
                        self.compute_proximity_sticky_magnet(context, stick=event.ctrl)# on line with stickiness ctrl
            
            # ## Store mouse position in a variable
            
            # ## Store mouse path in a list (only if left click is pressed)
            # if self.pressed_key == 'LEFTMOUSE':# This is evaluated as a continuous press
            #     # self.mouse_paVector(th.app)end((event.mouse_region_x, event.mouse_region_y))
            #     pass

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
        if event.type in {'RET', 'SPACE'}:
            self.stop_modal(context)
            
            ## depth correction
            for i, p in enumerate(self.mv_points):
                p.co = self.matworld.inverted() @ mathutils.geometry.intersect_line_plane(self.view_co, self.matworld @ p.co, self.plane_co, self.plane_no)

            ## autoclean overlapping vertices
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
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        context.area.tag_redraw()
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
        self.mouse = Vector((0, 0)) # updated tuple of mouse coordinate
        self.mouse_prev = None # updated tuple of mouse coordinate
        self.initial_ms = (event.mouse_region_x, event.mouse_region_y)
        
        ## Starts the modal
        display_text = 'Magnet Brush mode | Valid: Space, Enter | Cancel: Right Click, Escape |'
        if material_targets and mat_ids:
            display_text += f' Target materials: "{"|".join(material_targets)}"'


        ## brush settings
        self.pen_radius = context.scene.gp_magnetools.mgnt_radius#10 # use a scene prop here (or check sculpt radius)
        self.crosshair_resolution = 16# hardcode for now(4,8,12,16,20...) keep multiple of 4

        context.area.header_text_set(display_text)
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(GPMGT_OT_magnet_brush)
    # for cls in classes:
        # bpy.utils.register_class(cls)


def unregister():
    bpy.utils.unregister_class(GPMGT_OT_magnet_brush)
    # for cls in reversed(classes):
        # bpy.utils.unregister_class(cls)