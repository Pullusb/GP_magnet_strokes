import bpy
import numpy as np
import mathutils
from bpy_extras import view3d_utils
from mathutils import Vector
from math import sqrt

def get_last_index(context=None):
    if not context:
        context = bpy.context
    return 0 if context.tool_settings.use_gpencil_draw_onback else -1

# -----------------
### Vector utils 2d
# -----------------

def location_to_region(worldcoords):
    return view3d_utils.location_3d_to_region_2d(bpy.context.region, bpy.context.space_data.region_3d, worldcoords)

def region_to_location(viewcoords, depthcoords):
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