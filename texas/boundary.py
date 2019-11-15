import os
import math
from compas_fofin.datastructures import Cablenet
from compas_rhino.artists import MeshArtist
from compas_rhino.artists import FrameArtist
from compas_rhino.artists import PointArtist
from compas.datastructures import Mesh
from compas.geometry import add_vectors, Vector
from compas.geometry import scale_vector
from compas.geometry import Frame
from compas.geometry import Transformation
from compas.geometry import transform_points
from compas.geometry import cross_vectors
from compas.geometry import subtract_vectors
from compas.geometry import bounding_box_xy
from compas.geometry import offset_polygon
from compas.geometry import intersection_line_plane

# ==============================================================================
# Create a proxy for PCA
# ==============================================================================

from compas.rpc import Proxy

numerical = Proxy('compas.numerical')
pca_numpy = numerical.pca_numpy


# ==============================================================================
# Methods
# ==============================================================================


def get_bbox(pts):
    if len(pts) < 3:
        return None

    origin, axes, values = pca_numpy([list(pt) for pt in pts])
    v = pca_numpy([list(pt) for pt in pts])

    frame = Frame(origin, axes[0], axes[1])
    xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())

    pts = transform_points(pts, xform)
    bbox = bounding_box_xy(pts)
    bbox = offset_polygon(bbox, -PADDING)

    return bbox


def flip_vector(vector):
    return vector[0] * -1, vector[1] * -1, vector[2] * -1


def get_bbox_vertices(bbox):
    vectors = [scale_vector(v[0], v[1]) for v in zip(bbox[1], bbox[2])]
    v = add_vectors(vectors[0], vectors[1])
    v = add_vectors(v, vectors[2])
    return [add_vectors(bbox[0], v)]
    # add_vectors(bbox[0], add_vectors(add_vectors(flip_vector(vectors[0]), flip_vector(vectors[1])), vectors[2])),
    # add_vectors(bbox[0], add_vectors(add_vectors(vectors[0], flip_vector(vectors[1])), vectors[2])),
    # add_vectors(bbox[0], add_vectors(add_vectors(vectors[0], vectors[1]), vectors[2])),
    # add_vectors(bbox[0], add_vectors(add_vectors(flip_vector(vectors[0]), vectors[1]), vectors[2])),
    # add_vectors(bbox[0], add_vectors(add_vectors(flip_vector(vectors[0]), flip_vector(vectors[1])),
    #                                  flip_vector(vectors[2]))),
    # add_vectors(bbox[0], add_vectors(add_vectors(vectors[0], flip_vector(vectors[1])), flip_vector(vectors[2]))),
    # add_vectors(bbox[0], add_vectors(add_vectors(vectors[0], vectors[1]), flip_vector(vectors[2]))),
    # add_vectors(bbox[0], add_vectors(add_vectors(flip_vector(vectors[0]), vectors[1]), flip_vector(vectors[2])))


def extrude_normal(polygon, distance):
    x, y, z = cross_vectors(subtract_vectors(polygon[0], polygon[1]), subtract_vectors(polygon[0], polygon[2]))
    normal = Vector(x, y, z)
    Vector.unitize(normal)
    normal = scale_vector(normal, distance)
    # normal = Vector(x, y, z)

    moved = [add_vectors(pt, normal) for pt in polygon]
    polygon.extend(moved)
    return polygon


def check_size(points, max_x=0.0, max_y=0.0):
    fit = True
    x = get_distance(points[1], points[0])
    y = get_distance(points[3], points[0])
    if 0 < max_x < x:
        fit = False
    if 0 < max_y < y:
        fit = False
    return fit


def get_distance(point0, point1):
    return math.sqrt(
        math.pow(point0[0] - point1[0], 2.0) + math.pow(point0[1] - point1[1], 2.0) + math.pow(point0[2] - point1[2],
                                                                                               2.0))


# ==============================================================================
# Make a cablenet.
# ==============================================================================


HERE = os.path.dirname(__file__)
FILE_I = os.path.join(HERE, 'data', 'cablenet.json')

# cablenet: Cablenet = Cablenet.from_json(FILE_I)
cablenet = Cablenet.from_json(FILE_I)

# ==============================================================================
# Parameters
# ==============================================================================

OFFSET = 0.200
PADDING = 0.020

# ==============================================================================
# Vertices on South
# ==============================================================================

SOUTH = list(cablenet.vertices_where({'constraint': 'SOUTH'}))
boundary = list(cablenet.vertices_on_boundary(ordered=True))
SOUTH[:] = [key for key in boundary if key in SOUTH]

# ==============================================================================
# Boundary plane
# ==============================================================================

a = cablenet.vertex_coordinates(SOUTH[0])
b = cablenet.vertex_coordinates(SOUTH[-1])

xaxis = subtract_vectors(b, a)
yaxis = [0, 0, 1.0]
zaxis = cross_vectors(xaxis, yaxis)

xaxis = cross_vectors(yaxis, zaxis)

frame = Frame(a, xaxis, yaxis)

point = add_vectors(frame.point, scale_vector(frame.zaxis, OFFSET))
normal = frame.zaxis
plane = point, normal

# ==============================================================================
# Intersections
# ==============================================================================

intersections = []

for key in SOUTH:
    a = cablenet.vertex_coordinates(key)
    r = cablenet.residual(key)
    b = add_vectors(a, r)
    pt = intersection_line_plane((a, b), plane)

    intersections.append(pt)

# points = intersections[:3]
# bbox = pca_numpy([list(pt) for pt in points])
# xform = Transformation.from_frame_to_frame(plane, Frame.worldXY())
# xformed = transform_points(points, xform)
# offset_polygon(xformed, -PADDING)
#

# ==============================================================================
# Select the first 6 vertices of the boundary for the first segment of the
# supporting structure. Compute a local frame for the selected vertices using a
# PCA of the vertex locations.
# ==============================================================================

boxes = []
start = 0
end = len(intersections)

flag = True

# while flag:
#     for index in range(start, end + 1):
#         if index == end:
#             flag = False
#             break
#         pts = intersections[start:index]
#         if len(pts) < 3:
#             continue
#         bbox = pca_numpy(pts)
#         frame1 = Frame(bbox[0], bbox[1][0], bbox[1][1])
#         xform = Transformation.from_frame_to_frame(frame1, Frame.worldXY())
#         pts = transform_points(pts, xform)
#         bbox = bounding_box_xy(pts)
#         bbox = offset_polygon(bbox, -PADDING)
#         fit = check_size(bbox, 1.8, 0.3)
#         if not fit:
#             pts = intersections[start:index - 1]
#             bbox = transform_points(bbox, xform.inverse())
#             box = extrude_normal(bbox, 0.02)
#             boxes.append(box)
#             start = index - 1


while flag:
    for index in range(start, end):
        if index >= end:
            flag = False
            break
        pts = intersections[start:end - index]
        if len(pts) < 3:
            continue
        bbox = pca_numpy(pts)
        frame1 = Frame(bbox[0], bbox[1][0], bbox[1][1])
        xform = Transformation.from_frame_to_frame(frame1, Frame.worldXY())
        pts = transform_points(pts, xform)
        bbox = bounding_box_xy(pts)
        bbox = offset_polygon(bbox, -PADDING)
        fit = check_size(bbox, 1.8, 0.3)
        if fit:
            pts = intersections[index:end]
            bbox = transform_points(bbox, xform.inverse())
            box = extrude_normal(bbox, 0.02)
            boxes.append(box)
            end = index


# ==============================================================================
# Convert the box to a mesh for visualisation.
# ==============================================================================
faces = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
meshes = [Mesh.from_vertices_and_faces(points, faces) for points in boxes]

# ==============================================================================
# Use a frame artist to visualize the boundary frame.
# ==============================================================================


artist = FrameArtist(frame, layer="SOUTH::Frame", scale=0.3)
artist.clear_layer()
artist.draw()

# ==============================================================================
# Use a point artist to visualize the intersection points.
# ==============================================================================

PointArtist.draw_collection(intersections, layer="SOUTH::Intersections", clear=True)

# ==============================================================================
# Use a frame artist to visualize the frame of the intersection points.
# ==============================================================================

artist = FrameArtist(frame1, layer="SOUTH::Frame1", scale=0.3)
artist.clear_layer()
artist.draw()

# ==============================================================================
# Use a mesh artist to visualize the bounding box.
# ==============================================================================
artist = MeshArtist(None, layer="SOUTH::Bbox1")
artist.clear_layer()

for mesh in meshes:
    artist = MeshArtist(mesh, layer="SOUTH::Bbox1")
    artist.draw_mesh()
