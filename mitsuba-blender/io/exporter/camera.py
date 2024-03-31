import numpy as np
import bpy
from mathutils import Matrix
from math import degrees

def export_camera(camera_instance, b_scene, export_ctx):
    #camera
    b_camera = camera_instance.object#TODO: instances here too?
    params = {}
    params['type'] = 'perspective'

    res_x = b_scene.render.resolution_x
    res_y = b_scene.render.resolution_y

    # Extract fov
    sensor_fit = b_camera.data.sensor_fit
    if sensor_fit == 'AUTO':
        params['fov_axis'] = 'x' if res_x >= res_y else 'y'
        params['fov'] = degrees(b_camera.data.angle_x)
    elif sensor_fit == 'HORIZONTAL':
        params['fov_axis'] = 'x'
        params['fov'] = degrees(b_camera.data.angle_x)
    elif sensor_fit == 'VERTICAL':
        params['fov_axis'] = 'y'
        params['fov'] = degrees(b_camera.data.angle_y)
    else:
        export_ctx.log(f'Unknown \'sensor_fit\' value when exporting camera: {sensor_fit}', 'ERROR')

    params["principal_point_offset_x"] = b_camera.data.shift_x / res_x * max(res_x, res_y)
    params["principal_point_offset_y"] = -b_camera.data.shift_y / res_y * max(res_x, res_y)

    #TODO: test other parameters relevance (camera.lens, orthographic_scale, dof...)
    params['near_clip'] = b_camera.data.clip_start
    params['far_clip'] = b_camera.data.clip_end
    #TODO: check that distance units are consistent everywhere (e.g. mm everywhere)
    #TODO enable focus thin lens / cam.dof

    init_rot = Matrix.Rotation(np.pi, 4, 'Y')
    params['to_world'] = export_ctx.transform_matrix(b_camera.matrix_world @ init_rot)

    if b_scene.render.engine == 'MITSUBA':
        sampler = getattr(b_camera.data.mitsuba.samplers, b_camera.data.mitsuba.active_sampler).to_dict()
    else:
        sampler = {'type' : 'independent'}
        sampler['sample_count'] = b_scene.cycles.samples

    params['sampler'] = sampler

    film = {}
    film['type'] = 'hdrfilm'

    scale = b_scene.render.resolution_percentage / 100
    film['width'] = int(res_x * scale)
    film['height'] = int(res_y * scale)


    if b_scene.render.engine == 'MITSUBA':
        film['rfilter'] = getattr(b_camera.data.mitsuba.rfilters, b_camera.data.mitsuba.active_rfilter).to_dict()
    elif b_scene.render.engine == 'CYCLES':
        # INS: Changed to only box filter
        film['rfilter'] = {'type' : 'box'}

    params['film'] = film

    # INS: We always name our camera to 'camera'
    export_ctx.data_add(params, name='camera')

    # INS: Store the transforms over for animation
    start_frame = b_scene.frame_start
    end_frame = b_scene.frame_end
    init_rot = Matrix.Rotation(np.pi, 4, 'Y')
    to_worlds = []
    for frame in range(start_frame, end_frame+1):
        bpy.context.scene.frame_set(frame)
        to_world = export_ctx.transform_matrix(b_camera.matrix_world @ init_rot).matrix.numpy()
        to_worlds.append(to_world)

    # Naive test to check if the camera is stationary
    to_worlds = np.asarray(to_worlds)
    diff = to_worlds[1:] - to_worlds[:1,...]
    if np.allclose(diff, 0):
        to_worlds = []
    else:
        to_worlds = to_worlds.tolist()

    return to_worlds