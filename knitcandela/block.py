import os
from compas_fofin.datastructures import Cablenet
from compas_rhino.artists import MeshArtist, FrameArtist, LineArtist
from compas.datastructures import Mesh
from compas.datastructures import mesh_flip_cycles
from compas.geometry import add_vectors, intersection_line_plane, Frame, Line, Plane
from compas.geometry import scale_vector, cross_vectors, subtract_vectors

# ==============================================================================
# Set the path to the input file.
# ==============================================================================

HERE = os.path.dirname(__file__)
FILE_I = os.path.join(HERE, 'data', 'cablenet.json')

# ==============================================================================
# Make a cablenet.
# ==============================================================================

# cablenet: Cablenet = Cablenet.from_json(FILE_I)
cablenet = Cablenet.from_json(FILE_I)

# ==============================================================================
# Flip the cycles of the mesh because the cycles are currently such that the
# normals point to the interior of the structure.
# Note that you could also just flip the cycles once and update the JSON file.
# ==============================================================================

mesh_flip_cycles(cablenet)

# ==============================================================================
# Set the value of the thickness of the foam blocks in [m].
# ==============================================================================

THICKNESS = 0.200

# ==============================================================================
# Randomly select a face to create one block.
# ==============================================================================

face_key = cablenet.get_any_face()

# ==============================================================================
# Get the vertices of the selected face.
# The vertices are always in cycling order.
# ==============================================================================

vertices = cablenet.face_vertices(face_key)

# ==============================================================================
# Look up the coordinates of the face vertices and the normals at those vertices.
# Note that the normals are not stored as attributes, but rather have to be
# computed based on the current geometry.
# Therefore, there is no variant of the `get_vertices_attributes` that can be
# used to look up the vertex normals.
# ==============================================================================

points = cablenet.get_vertices_attributes('xyz', keys=vertices)
normals = [cablenet.vertex_normal(key) for key in vertices]

# ==============================================================================
# The bottom face of the block is formed by the vertices of the face of the
# cablenet. The top vertices of the block are offset along the normal at each
# vertex by the intended thickness of the block.
# Note that this will not result in a block with constant thickness, because the
# normals are generally not parallel. To create a block with constant thickness
# you have to use the face normal to find a parallel offset plane and then
# intersect each of the normal directions at the vertices with this plane.
# ==============================================================================

face_normal = cablenet.face_normal(face_key)
face_normal = scale_vector(face_normal, THICKNESS)
point = add_vectors(points[0], face_normal)

top_plane = (point, face_normal)


# bottom_points = points[:]
# top_points = []
# for start, normal in zip(points, normals):
# end = add_vectors(point, scale_vector(normal, THICKNESS))
#
# intersection = intersection_line_plane((line.start, line.end), top_plane)
# top_points.append(intersection)
#
# line_artist = LineArtist(lines[0], layer="test")
# line_artist.draw_collection(lines, layer='test', clear=True)
# ==============================================================================
# The vertices of the block mesh are simply the vertices of the bottom and top
# faces. The faces themselves are defined such that once the block is formed
# all face normals point towards the exterior of the block.
# Note that this means that the order of the vertices of the bottom block has
# to be reversed.
# ==============================================================================

# vertices = bottom_points + top_points
# faces = [[0, 3, 2, 1], [4, 5, 6, 7], [3, 0, 4, 7], [2, 3, 7, 6], [1, 2, 6, 5], [0, 1, 5, 4]]
#
# block = Mesh.from_vertices_and_faces(vertices, faces)
#
# # ==============================================================================
# # Visualize the block with a mesh artist in the specified layer. Use
# # `draw_faces` (with `join_faces=True`) instead of `draw_mesh` to get a flat
# # shaded result. Also draw the vertex labels tov isualize the cycle directions.
# # ==============================================================================
#
# artist = MeshArtist(block, layer="Boxes::Test")
# artist.clear_layer()
# artist.draw_faces(join_faces=True, color=(0, 255, 255))
# artist.draw_vertexlabels()
#
# d = top_plane[0][0]*top_plane[1][0] + top_plane[0][1]*top_plane[1][1] + top_plane[0][2]*top_plane[1][2]
# point_on_plane = [0, 0, -d/top_plane[1][2]]
# axis_0 = subtract_vectors(top_plane[0], point_on_plane)
# axis_1 = cross_vectors(top_plane[1], axis_0)
plane = Plane(top_plane[0], top_plane[1])
artist = FrameArtist(Frame.from_plane(plane), layer='Planes::Top planes')
artist.clear_layer()
artist.draw()

bottom = points[:]
top = []
lines = []
for point, normal in zip(points, normals):
    xyz = add_vectors(point, scale_vector(normal, THICKNESS))
    line = (point, xyz)
    intersection = intersection_line_plane(line, top_plane)
    top.append(intersection)
    lines.append(Line(point, intersection))
line_artist = LineArtist(lines[0], layer="test")
line_artist.draw_collection(lines, layer='test', clear=True)

# ==============================================================================
# The vertices of the block mesh are simply the vertices of the bottom and top
# faces. The faces themselves are defined such that once the block is formed
# all face normals point towards the exterior of the block.
# Note that this means that the order of the vertices of the bottom block has
# to be reversed.
# ==============================================================================

vertices = bottom + top
faces = [[0, 3, 2, 1], [4, 5, 6, 7], [3, 0, 4, 7], [2, 3, 7, 6], [1, 2, 6, 5], [0, 1, 5, 4]]

block = Mesh.from_vertices_and_faces(vertices, faces)

# ==============================================================================
# Visualize the block with a mesh artist in the specified layer. Use
# `draw_faces` (with `join_faces=True`) instead of `draw_mesh` to get a flat
# shaded result. Also draw the vertex labels tovisualize the cycle directions.
# ==============================================================================

artist = MeshArtist(block, layer="Boxes::Test")
artist.clear_layer()
artist.draw_faces(join_faces=True, color=(0, 255, 255))
artist.draw_vertexlabels()

