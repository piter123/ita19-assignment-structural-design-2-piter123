import json
import os
from compas_fofin.datastructures import Cablenet
from compas_rhino.artists import MeshArtist, FrameArtist, LineArtist
from compas.datastructures import Mesh
from compas.datastructures import mesh_flip_cycles
from compas.geometry import add_vectors, intersection_line_plane, Frame, Line, Plane, offset_polygon, Transformation, \
    transform_points
from compas.geometry import scale_vector, cross_vectors, subtract_vectors


# ==============================================================================
# Methods
# ==============================================================================

# def offset_curve_xy(pts, dist):
#     bbox = pca_numpy(pts)
#     frame1 = Frame(bbox[0], bbox[1][0], bbox[1][1])
#     xform = Transformation.from_frame_to_frame(frame1, Frame.worldXY())
#     pts = transform_points(pts, xform)
#     bbox = bounding_box_xy(pts)
#     bbox = offset_polygon(bbox, dist)
#         bbox = transform_points(bbox, xform.inverse())
#     return bbox, xform


def line_sdl(start, direction, length=0.0):
    if length > 0.0:
        direction = scale_vector(direction, length)
    end = add_vectors(start, direction)
    return Line(start, end)


def point_on_plane(point, frame, direction=None):
    if direction is None:
        direction = frame.normal
    line = line_sdl(point, direction, 1.0)
    return intersection_line_plane((line.start, line.end), (frame.point, frame.normal))


def offset_polygon_xy(points, dist, planarize=False):
    if len(points) < 3:
        return None
    frame = Frame.from_plane(Plane.from_three_points(points[0], points[1], points[2]))
    xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
    if planarize:
        points = [point_on_plane(point, frame) for point in points]
    points = transform_points(points, xform)
    points = offset_polygon(points, dist)
    points = transform_points(points, xform.inverse())
    return points


def join_meshes(meshes):
    joined = Mesh()
    for mesh in meshes:
        for f in mesh.faces():
            vertices = mesh.face_vertices(f)
            points = mesh.get_vertices_attributes('xyz', keys=vertices)
            for p in points:
                joined.add_vertex(x=p[0], y=p[1], z=p[2])
            joined.add_face(vertices)
    return joined


def meshes_to_json(meshes, filepath, pretty=False):
    with open(filepath, 'a+') as fp:
        fp.truncate(0)
        for mesh in meshes:
            if pretty:
                json.dump(mesh.data, fp, sort_keys=True, indent=4)
            else:
                json.dump(mesh.data, fp)


# ==============================================================================
# Set the path to the input file.
# ==============================================================================
HERE = os.path.dirname(__file__)
FILE_I = os.path.join(HERE, 'data', 'cablenet.json')
# ==============================================================================
# Main
# ==============================================================================
# cablenet: Cablenet = Cablenet.from_json(FILE_I)
cablenet = Cablenet.from_json(FILE_I)

mesh_flip_cycles(cablenet)
THICKNESS = 0.200
OFFSET_0 = 0.02
OFFSET_1 = 0.03

# ==============================================================================
# Build blocks
# ==============================================================================
blocks = []

for face_key in cablenet.faces():
    vertices = cablenet.face_vertices(face_key)
    points = cablenet.get_vertices_attributes('xyz', keys=vertices)
    normals = [cablenet.vertex_normal(key) for key in vertices]

    face_normal = cablenet.face_normal(face_key)
    face_normal = scale_vector(face_normal, THICKNESS)
    point = add_vectors(points[0], face_normal)
    top_plane = Frame.from_plane(Plane(point, face_normal))

    bottom = points[:]
    top = []
    for point, normal in zip(points, normals):
        pt = point_on_plane(point, top_plane, normal)
        top.append(pt)

    bottom = offset_polygon_xy(bottom, OFFSET_0)
    top = offset_polygon_xy(top, OFFSET_1, True)

    vertices = bottom + top

    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [3, 0, 4, 7], [2, 3, 7, 6], [1, 2, 6, 5], [0, 1, 5, 4]]
    block = Mesh.from_vertices_and_faces(vertices, faces)
    blocks.append(block)
# ==============================================================================
# Visualize blocks
# ==============================================================================
artist = MeshArtist(None, layer="Boxes::Test")
artist.clear_layer()

for block in blocks:
    artist = MeshArtist(block, layer="Boxes::Test")
    artist.draw_faces(join_faces=True, color=(0, 255, 255))


# ==============================================================================
# Serialize meshes -- trick, not really working...
# ==============================================================================
meshes_to_json(blocks, HERE + "\\meshes.json", True)

# m = Mesh.from_json(HERE + "\\meshes.json")
# artist = MeshArtist(m, layer="Boxes::Test")
# artist.draw_faces(join_faces=True, color=(0, 255, 255))
