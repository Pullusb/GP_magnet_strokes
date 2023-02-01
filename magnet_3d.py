from . import func

import bpy
import mathutils
from time import time
from mathutils import Vector


class GPMGT_OT_magnet_by_3d_distance(bpy.types.Operator):
    bl_idname = "gp.magnet_by_3d_distance"
    bl_label = "Magnet Points By 3D distance"
    bl_description = "Try to magnet grease pencil stroke to closest strokes using 3d distance to points"
    bl_options = {"REGISTER", "UNDO"}

    # @classmethod
    # def poll(cls, context):
    #     return context.object is not None and context.object.type == 'GPENCIL'
    
    def execute(self, context):
        t0 = time()
        ## For now, snap all fills to lines !

        factor = 1 + bpy.context.scene.gp_magnetools.mgnt_3d_under_line_margin / 100
        # objs = [o for o in context.scene.objects if o.type == 'GPENCIL']
        objs = [context.object]

        for O in objs:
            ids = func.get_material_ids(O.data.materials)
            if not ids:
                print(f'{O.name} has no material from list')
                continue

            gpl = O.data.layers
            for L in gpl:
                print(L.info)
                ## pre filter with prefix ;)
                # if not L.info.startswith('CO_'):continue

                ### Point algo
                '''
                line_points = []
                for F in L.frames:
                    # Gather all visible strokes on this frame
                    for lay in [l for l in gpl if not l.hide and not l is L]:
                        # find same frame (TODO: should use a past frames if not exact same num)
                        frame = next((f for f in lay.frames if f.frame_number == F.frame_number), None)
                        if not frame:
                            continue
                        for s in frame.strokes:
                            if s.material_index not in ids:
                                continue
                            # divided by two because we want radius not diameter
                            line_points += [(p.co, p.pressure * (s.line_width / 2) / 1000) for p in s.points]

                    Thicknesses = [i[1] for i in line_points]
                    print('Thicknesses', min(Thicknesses), max(Thicknesses))
                    for S in F.strokes:
                        for pt in S.points:
                            # Search with a kdTree.
                            co, index, dist = find_vec_in_vecs(pt.co, line_points)
                            if dist > line_points[index][1]:
                                continue
                            # print(dist, '<', line_points[index][1])
                            pt.co = co
                '''
                ### Line algo (Way more robust)
                line_points = []
                for F in L.frames:
                    # Gather all visible strokes on this frame
                    for lay in [l for l in gpl if not l.hide and not l == L]:
                        # print('- ', lay.info)

                        ## find same frame (TODO: should use a past frames if not exact same num)
                        frame = next((f for f in lay.frames if f.frame_number == F.frame_number), None)
                        if not frame:
                            continue
                        for s in frame.strokes:
                            if s.material_index not in ids:
                                continue
                            
                            ## pressure: line_width / 2 (radius) multiplied by pressure, all divided by 1000 to get bl_unit
                            # Sublist instead of extend
                            # line_points.append([(p.co, p.pressure * (s.line_width / 2) / 1000) for p in s.points])
                            
                            ## with factor
                            line_points.append([(p.co, (p.pressure * (s.line_width / 2) / 1000) * factor) for p in s.points])

                    if not line_points:
                        continue
                    print(f'{len(line_points)} strokes to evaluate')
                    for S in F.strokes:
                        for pt in S.points:
                            co = check_proximity_to_lines(pt.co, line_points)
                            if not co:
                                continue
                            pt.co = co

        print(f'Elapsed{time() - t0:.2f}s')
        #self.autoclean(context)
        self.report({'INFO'}, "Magnet 3D applyed")
        return {'FINISHED'}

def check_proximity_to_lines(co_find, target_strokes):
    '''Only valid if distance is under point radius'''
    #reset
    prevdist = 10000
    res = None

    for stroke_pts in target_strokes:
        for i in range(len(stroke_pts)-1):
            ## Point (stroke_pts[i]) is a tuple (coord, radius)
            pos, percentage = mathutils.geometry.intersect_point_line(co_find, stroke_pts[i][0], stroke_pts[i+1][0])

            thick = stroke_pts[i][1]
            ## Use first thickness
            ## TODO: to gain precision, modulate by percentage to have the real thickness value


            if percentage <= 0: # head
                pos, thick = stroke_pts[i]
            
            elif 1 <= percentage: # tail
                pos, thick = stroke_pts[i+1]

            ## Check distance against previous
            
            dist = (pos - co_find).length
            if dist > thick:
                continue
                # skip if not under stroke radius
            
            # print('> ', pos, dist, thick)

            if dist < prevdist:
                res = pos
                prevdist = dist
                # break ??? (slighly dangerous, maybe test for perfs...)
        
    return res

def find_vec_in_vecs(co_find, points_pair):
    kd = mathutils.kdtree.KDTree(len(points_pair))
    for i, pair in enumerate(points_pair):
        kd.insert(pair[0], i)
    kd.balance()
    co, index, dist = kd.find(co_find)
    return co, index, dist


## test zone

def create_sphere(loc, radius):
    # get create collection
    col_name = 'Conjunction of the spheres'
    if not (col := bpy.data.collections.get(col_name)):
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)

    ## create a pseudo sphere by hand
    # ob_data = bpy.data.meshes.new("ball")
    # ob_name = 'ball'

    # ## need to fill mesh with a verts...
    # ob = bpy.data.objects.new(ob_name, ob_data)

    # link object
    # col.objects.link(ob)
    # ob.location = loc
    # ob.dimensions = [radius * 2] * 3 # diamater

    ## create a sphere with ops
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32, ring_count=16, radius=radius,
        enter_editmode=False, align='WORLD', location=loc)
    ob = bpy.context.object
    if bpy.context.collection.name != col_name:
        bpy.context.collection.objects.unlink(ob)
        col.objects.link(ob)


def create_balls():
    factor = bpy.context.scene.gp_magnetools.mgnt_3d_under_line_margin / 100
    if not bpy.context.object:
        print('Nothing active')
        return
    s = next((s for s in bpy.context.object.data.layers.active.active_frame.strokes if s.select), None)
    if not s:
        print('no stroke selected in active frame of active layer')
        return
    for p in s.points:
        if p.select:
            radius = p.pressure * (s.line_width / 2) / 1000
            radius = radius + radius * factor
            # print('radius:', radius)
            create_sphere(p.co, radius)

class GPMGT_OT_test_radius(bpy.types.Operator):
    bl_idname = "gp.test_radius"
    bl_label = "Test Radius"
    bl_description = "Test radius calculation accuracy by adding mesh spheres"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        create_balls()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(GPMGT_OT_magnet_by_3d_distance)
    bpy.utils.register_class(GPMGT_OT_test_radius)

def unregister():
    bpy.utils.unregister_class(GPMGT_OT_magnet_by_3d_distance)
    bpy.utils.unregister_class(GPMGT_OT_test_radius)

