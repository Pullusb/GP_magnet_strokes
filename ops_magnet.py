from .func import *

import bpy
import mathutils
from mathutils import Vector
from time import time#Dbg-time


class GPMGT_OT_magnet_gp_lines_all(bpy.types.Operator):
    bl_idname = "gp.magnet_lines_all"
    bl_label = "Magnet all gp lines once"
    bl_description = "Try to magnet grease pencil stroke to closest stroke"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'GPENCIL'

    point_snap : bpy.props.BoolProperty(
        name="Snap to points", description="Snap on points instead of lines (Better performance)", 
        default=False, options={'HIDDEN'})

    tolerance : bpy.props.IntProperty(
        name="Magnet Distance", description="Area of effect of the magnet (radius around point in pixel value)", 
        default=25, soft_min=1, step=1, subtype='PIXEL', options={'HIDDEN'})


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


    def compute_point_proximity_magnet(self, context):
        '''To point directly (faster)'''
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

            ## Use a proximity a snap with tolerance:
            if prevdist <= self.tolerance:
                #res is 2d, need 3d coord
                self.mv_points[j].co = self.matworld.inverted() @ region_to_location(res, self.depth)
            else:
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

    def execute(self, context):
        if self.point_snap:
            self.compute_point_proximity_magnet(context)
        else:
            self.compute_proximity_magnet(context)

        ## depth correction
        for p in self.mv_points:
            p.co = self.matworld.inverted() @ mathutils.geometry.intersect_line_plane(self.view_co, self.matworld @ p.co, self.plane_co, self.plane_no)
        
        self.autoclean(context)
        self.report({'INFO'}, "Magnet applyed")
        return {'FINISHED'}


    # def draw(self, context):
    #     layout = self.layout
    #     layout.label(text = 'magnet parameters')
    #     layout.prop(self, "tolerance")
    #     layout.prop(self, "point_snap")

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
        
        margin = 25
        area_x = -margin# context.area.x + 
        area_y = -margin# context.area.y + 
        area_mx = context.area.width + margin
        area_my = context.area.height + margin


        # self.target_points = []
        # self.target_2d_co = []
        self.matworld = ob.matrix_world
        gpl = ob.data.layers

        if not gpl.active:
            self.report({'ERROR'}, f"No active layers on GP object")
            return {'CANCELLED'}

        ## target layers        
        extend = settings.mgnt_near_layers_targets
        if extend < 0:
            tgts = [l for i, l in enumerate(gpl) if gpl.active_index > i >=  gpl.active_index + extend]
        
        elif extend > 0:
            tgts = [l for i, l in enumerate(gpl) if gpl.active_index < i <=  gpl.active_index + extend]
        
        else:# extend == 0
            tgts = [l for i, l in enumerate(gpl) if i != gpl.active_index]

        tgt_layers = [l for l in tgts if not l.hide] # and l != gpl.active
        
        if not tgt_layers:# No target found
            self.report({'ERROR'}, f"No layers targeted, Check filters (Note: can only other layers than active)")
            return {'CANCELLED'}

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

                ## direct append (if no need to check coordinates against placement in view (or kdtree in the future))
                # self.target_strokes.append([location_to_region(self.matworld @ p.co) for p in s.points])

                tgt_2d_pts_list = [location_to_region(self.matworld @ p.co) for p in s.points]
                
                ## visibility check (check all point in stroke)
                # ok=False
                # for p in tgt_2d_pts_list:
                #     if area_x < p[0] < area_mx and area_y < p[1] < area_my:
                #         ok=True
                #         break
                
                ## visibility check Quick (checking only first and last point of stroke)
                ok = area_x < tgt_2d_pts_list[0][0] < area_mx and area_y < tgt_2d_pts_list[0][1] < area_my\
                    or area_x < tgt_2d_pts_list[-1][0] < area_mx and area_y < tgt_2d_pts_list[-1][1] < area_my
                
                if not ok:
                    continue
                self.target_strokes.append(tgt_2d_pts_list)

                
                ##### POINT MODE: All mixed points pairs (valid for direct point search, dont take strokes gap for line search) 
                # for p in s.points:
                #     self.target_points.append(p)
                #     self.target_2d_co.append(location_to_region(self.matworld @ p.co))
       

        # print(f'End target line infos get: {time() - start_init:.4f}s')#Dbg-time
        if not self.target_strokes:
            self.report({'ERROR'}, "No target strokes found")
            return {'CANCELLED'}

        print(f'{len(self.target_strokes)} target strokes')#Dbg
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

        return self.execute(context)


def register():
    bpy.utils.register_class(GPMGT_OT_magnet_gp_lines_all)

def unregister():
    bpy.utils.unregister_class(GPMGT_OT_magnet_gp_lines_all)
