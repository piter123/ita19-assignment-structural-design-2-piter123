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

def extrude_normal(polygon, distance, plane=None):
    if plane is None:
        x, y, z = cross_vectors(subtract_vectors(polygon[0], polygon[1]), subtract_vectors(polygon[0], polygon[2]))
        normal = Vector(x, y, z)
    else:
        normal = plane.normal
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
        math.pow(point0[0] - point1[0], 2.0) + math.pow(point0[1] - point1[1], 2.0) +
        math.pow(point0[2] - point1[2], 2.0))


def get_boundary_plane(boundary):
    a = cablenet.vertex_coordinates(boundary[0])
    b = cablenet.vertex_coordinates(boundary[-1])

    x_axis = subtract_vectors(b, a)
    y_axis = [0, 0, 1.0]
    z_axis = cross_vectors(x_axis, y_axis)

    x_axis = cross_vectors(y_axis, z_axis)

    frame_0 = Frame(a, x_axis, y_axis)
    point = add_vectors(frame_0.point, scale_vector(frame_0.zaxis, OFFSET))
    frame_1 = Frame(point, x_axis, y_axis)
    return frame_0, frame_1


def intersect_residual(boundary, frame):
    intersections = []
    for key in boundary:
        a = cablenet.vertex_coordinates(key)
        r = cablenet.residual(key)
        b = add_vectors(a, r)
        pt = intersection_line_plane((a, b), (frame.point, frame.zaxis))
        intersections.append(pt)

    return intersections


def offset_bbox_xy(pts, dist):
    bbox = pca_numpy(pts)
    frame1 = Frame(bbox[0], bbox[1][0], bbox[1][1])
    xform = Transformation.from_frame_to_frame(frame1, Frame.worldXY())
    pts = transform_points(pts, xform)
    bbox = bounding_box_xy(pts)
    bbox = offset_polygon(bbox, dist)
    return bbox, xform


def build_meshes(boxes, plane):
    beams = [extrude_normal(box, BEAM_WIDTH, plane) for box in boxes]
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [3, 0, 4, 7], [2, 3, 7, 6], [1, 2, 6, 5], [0, 1, 5, 4]]
    # faces = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    meshes = [Mesh.from_vertices_and_faces(points, faces) for points in beams]
    return meshes


def compute_edge(orientation):
    # ==============================================================================
    # Evaluate geometry
    # ==============================================================================
    boundary = list(cablenet.vertices_where({'constraint': orientation}))
    ordered = list(cablenet.vertices_on_boundary(ordered=True))
    boundary[:] = [key for key in ordered if key in boundary]

    frames = get_boundary_plane(boundary)
    intersections = intersect_residual(boundary, frames[1])
    boxes = []
    # ==============================================================================
    # Fit support beams
    # ==============================================================================
    points = intersections
    while True:
        end = len(points)
        if end <= 2:
            break
        for index in range(0, end):
            pts = points[0: end - index]
            if len(pts) < 3:
                continue

            bbox, xform = offset_bbox_xy(pts, -PADDING)
            fit = check_size(bbox, MAX_SIZE[0], MAX_SIZE[1])
            if fit:
                bbox = transform_points(bbox, xform.inverse())
                boxes.append(bbox)
                points = points[end - (index + 1):]
                break
    # ==============================================================================
    # Build beams meshes
    # ==============================================================================
    meshes = build_meshes(boxes, frames[0])
    return {'meshes' : meshes, 'frames' : frames, 'intersections' : intersections, 'layer' : str(orientation)}


def draw_edge_rhino(edge):
    # ==============================================================================
    # Use a frame artist to visualize the boundary frame.
    # ==============================================================================
    artist = FrameArtist(edge['frames'][0], layer=edge['layer'] + "::Frame", scale=0.3)
    artist.clear_layer()
    artist.draw()
    # ==============================================================================
    # Use a frame artist to visualize the frame of the intersection points.
    # ==============================================================================
    artist = FrameArtist(edge['frames'][1], layer=edge['layer'] + "::Frame", scale=0.3)
    artist.clear_layer()
    artist.draw()
    # ==============================================================================
    # Use a point artist to visualize the intersection points.
    # ==============================================================================
    PointArtist.draw_collection(edge['intersections'], layer=edge['layer'] + "::Intersections", clear=True)
    # ==============================================================================
    # Use a mesh artist to visualize beams
    # ==============================================================================
    artist = MeshArtist(None, layer=edge['layer'] + "::BBox")
    artist.clear_layer()
    for mesh in edge['meshes']:
        artist = MeshArtist(mesh, layer=edge['layer'] + "::BBox")
        artist.draw_mesh()


# ==============================================================================
# Main
# ==============================================================================

HERE = os.path.dirname(__file__)
FILE_I = os.path.join(HERE, 'data', 'cablenet.json')

cablenet = Cablenet.from_json(FILE_I)
# cablenet: Cablenet = Cablenet.from_json(FILE_I)

# ==============================================================================
# Parameters
# ==============================================================================

OFFSET = 0.200
PADDING = 0.020
BEAM_WIDTH = 0.040
MAX_SIZE = (1.20, 0.20)

# ==============================================================================
# Run
# ==============================================================================

south = compute_edge('SOUTH')
north = compute_edge('NORTH')

# ==============================================================================
# Draw rhino geometry
# ==============================================================================

draw_edge_rhino(south)
draw_edge_rhino(north)
