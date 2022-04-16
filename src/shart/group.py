import math
import sys

import shapely as sh
import shapely.geometry
import shapely.ops
import shapely.affinity

import cairo

import shart.geom_attributes
from .geom_attributes import GeomAttributesManager, MutableGeomAttributesManager
from .utils import *


class Group:

    def __init__(self, geoms=None, geom_attributes_manager=None):
        if geoms is None:
            self.geoms = sh.geometry.MultiPolygon([])
            self.type = sh.geometry.MultiPolygon
        else:
            if not isinstance(geoms, sh.geometry.MultiPolygon) and not isinstance(geoms, sh.geometry.MultiLineString):
                raise ValueError(f"Unsupported geom type: {geoms}")

            self.geoms = geoms
            self.type = type(geoms)

        if geom_attributes_manager is None:
            self.geom_attributes_manager = GeomAttributesManager()
        elif not isinstance(geom_attributes_manager, GeomAttributesManager):
            raise ValueError(f"geom_attributes_manager is not an instance "
                             f"of GeomAttributesManager, instead: {type(geom_attributes_manager)}")
        else:
            self.geom_attributes_manager = geom_attributes_manager

    def explode(self):
        for i, g in enumerate(self.geoms.geoms):
            subgroup = Group(self.type([g]), self.geom_attributes_manager.extract_index(i))
            yield subgroup

    def add_geom_attribute(self, key, value):
        new_attrib_manager = self.geom_attributes_manager
        for i, g in enumerate(self.geoms.geoms):
            new_attrib_manager = new_attrib_manager.add_geom_attribute(i, key, value)

        return Group(self.geoms, new_attrib_manager)

    @property
    def bounds_x(self):
        return self.geoms.bounds[0]

    @property
    def bounds_y(self):
        return self.geoms.bounds[1]

    @property
    def bounds_mid_x(self):
        return self.bounds_x + self.bounds_width / 2

    @property
    def bounds_mid_y(self):
        return self.bounds_y + self.bounds_height / 2

    @property
    def bounds_width(self):
        return self.geoms.bounds[2] - self.geoms.bounds[0]

    @property
    def bounds_height(self):
        return self.geoms.bounds[3] - self.geoms.bounds[1]

    def anchor(self):
        # anchor is translation, which should preserve geom indices
        anchored_geoms = anchor_geom(self.geoms)(self.geoms)

        return Group(anchored_geoms, self.geom_attributes_manager)

    def border(self, border_thickness, border_radius):
        border_geom = create_border_box(self.geoms, border_thickness, border_radius)

        if self.type == sh.geometry.MultiLineString:
            border_geom = border_geom.boundary

        return Group(
            self.type(
                [g for g in self.geoms.geoms] + [border_geom]
            ), self.geom_attributes_manager)  # indices preserved as border is appended

    def filter(self, predicate):
        filtered_geoms = []
        filtered_gam = MutableGeomAttributesManager.copy(self.geom_attributes_manager)
        for i, g in enumerate(self.geoms.geoms):
            from_index = i

            predicate_group = Group.from_geomarray([g], self.geom_attributes_manager.extract_index(i))

            if predicate(predicate_group):
                to_index = len(filtered_geoms)

                # index of geom will change from i to len(filtered_geoms)
                filtered_gam.move_geom_attributes(from_index, to_index)
                filtered_geoms.append(g)
            else:
                filtered_gam.remove_geom_attributes(from_index)

        return Group.from_geomarray(filtered_geoms, filtered_gam.to_immutable())

    def do_and_add(self, modifier):
        return self.add(modifier(self))

    def do(self, modifier):
        return modifier(self)

    def map_subgroups(self, modifier):
        return Group().add_all(
            [modifier(g) for g in self.explode()]
        )

    def add(self, group):
        if not isinstance(group, Group):
            raise ValueError("Added group is of wrong type.")

        geom_array = [g for g in self.geoms.geoms] + [g for g in group.geoms.geoms]
        gam = self.geom_attributes_manager.union(
            group.geom_attributes_manager.offset_keys(len(self.geoms.geoms)))

        return Group(self.type(geom_array), gam)

    def add_all(self, groups):
        result_geomarray = [g for g in self.geoms.geoms]
        result_attributes = MutableGeomAttributesManager.copy(self.geom_attributes_manager)
        key_index_offset = len(result_geomarray)

        for g in groups:
            result_geomarray += [geom for geom in g.geoms.geoms]
            for k, v in g.geom_attributes_manager.attributes:
                result_attributes.add_attributes(k + key_index_offset, v)
            key_index_offset += len(g.geoms.geoms)

        return Group(self.type(result_geomarray), result_attributes.to_immutable())

    def intersection(self, group):
        intersections = (g.intersection(group.geoms) for g in self.geoms.geoms)

        if self.type == sh.geometry.MultiPolygon:
            # possible line intersections. these should be filtered out
            intersections = (i for i in intersections if i.type == "Polygon")

        return Group.from_geomarray(list(intersections))

    def difference(self, group):
        result = Group(self.type([]))

        for i, g in enumerate(self.geoms.geoms):
            g_diff = flatten_geoms([g.difference(group.geoms)])

            if len(g_diff) > 0:
                geom_attributes = self.geom_attributes_manager.get_geom_attributes(i)
                diff_group = Group(self.type(g_diff), GeomAttributesManager({0: geom_attributes}))
                result = result.add(diff_group)

        return result

    def union(self, geom=None):
        if geom is None:
            union = flatten_geoms([sh.ops.unary_union([g for g in self.geoms.geoms])])
            combined_attributes = dict()

            for k, d in self.geom_attributes_manager.attributes:
                combined_attributes.update(d)

            gam = MutableGeomAttributesManager()
            for i, g in enumerate(union):
                gam.add_attributes(i, combined_attributes)

            return Group(self.type(union), gam.to_immutable())

        elif isinstance(geom, Group):
            return self.add(geom).union()
        elif geom.type == "MultiPolygon" or geom.type == "MultiLineString":
            subgeoms = [g for g in geom.geoms]

            return Group.from_geomarray([sh.ops.unary_union(list(self.geoms.geoms) + subgeoms)])
        elif len(geom.geoms) == 0:
            # Union with an empty geom is just self
            return self
        else:
            return Group(
                sh.geometry.MultiPolygon([g.union(geom) for g in self.geoms.geoms])
            )

    def to(self, x_coord, y_coord, center=None):

        # if the user does not define a center, use the
        # geometric centroid
        cx = center[0] if center is not None else self.geoms.centroid.x
        cy = center[1] if center is not None else self.geoms.centroid.y

        dx = x_coord - cx
        dy = y_coord - cy

        return Group(sh.affinity.translate(self.geoms, dx, dy))

    def buffer(self, amount, resolution=16, join_style=sh.geometry.JOIN_STYLE.round, cap_style=sh.geometry.CAP_STYLE.round):
        return Group.from_geomarray([self.geoms.buffer(amount, resolution, join_style=join_style, cap_style=cap_style)])

    def translate(self, dx, dy):
        return Group(sh.affinity.translate(self.geoms, dx, dy), self.geom_attributes_manager)

    def scale(self, x, y=None, origin='center'):
        y = y or x

        return Group(sh.affinity.scale(self.geoms, xfact=x, yfact=y, origin=origin), self.geom_attributes_manager)

    def rotate(self, angle, use_radians=True, origin=None):
        if origin is None:
            origin = 'centroid'

        # rotations will preserve indices of sub-geometries
        return Group(
            sh.affinity.rotate(self.geoms, angle, use_radians=use_radians, origin=origin),
            self.geom_attributes_manager)

    def spin(self, center_x, center_y, count, geom_centroid=None, should_rotate=False):
        if geom_centroid is None:
            geom_centroid = self.geoms.centroid

        result = Group(self.type([]))
        angles = (a for a in np.linspace(0, 2 * math.pi, count, endpoint=False))
        for theta in angles:
            instance = self
            if not should_rotate:
                instance = instance.rotate(-theta, use_radians=True, origin=geom_centroid)

            instance = instance.rotate(theta, use_radians=True, origin=sh.geometry.Point(center_x, center_y))

            result = result.add(instance)

        return result

    def linarray(self, count, geom_modifier):
        result = Group()
        for i in range(0, count):
            new_geom = geom_modifier(i, self)
            result = result.add(new_geom)

        return result

    def recurse(self, modifier, depth):
        if depth == 0:
            return self

        result = []
        self._recurse(modifier, depth, result)

        return self.add_all(result)

    def _recurse(self, modifier, depth, result):
        if depth == 0:
            return

        subgroups = modifier(self)

        result += subgroups

        for g in subgroups:
            g._recurse(modifier, depth - 1, result)

    # todo: deprecated, use explode instead
    def foreach_modify(self, modifier):
        return Group.from_geomarray([modifier(g) for g in self.geoms.geoms], self.geom_attributes_manager)

    @staticmethod
    def circle(cx, cy, diameter, resolution=0.5):
        # resolution by default at least 1 step per 0.5mm
        divisions = max(1, int(math.pi * diameter * 0.25 / resolution))

        circle = sh.geometry.Point(cx, cy).buffer(diameter / 2, resolution=divisions)

        return Group(sh.geometry.MultiPolygon([
                circle
            ]))

    def covers(self, group):
        # returns true if any of this groups geoms cover ALL of
        # the supplied groups geoms
        for g in self.geoms.geoms:

            if all(g.covers(h) for h in group.geoms.geoms):
                return True

        return False

    def contains(self, group):
        # returns true if any of this groups geoms contain ALL of
        # the supplied groups geoms
        for g in self.geoms.geoms:

            if all(g.covers(h) and not g.crosses(h) for h in group.geoms.geoms):
                return True

        return False

    def intersects(self, group):
        # returns true if any of this groups geoms intersect ANY of
        # the supplied groups geoms
        for g in self.geoms.geoms:

            if any(g.intersects(h) for h in group.geoms.geoms):
                return True

        return False

    def to_boundary(self):
        if self.type != sh.geometry.MultiPolygon:
            raise ValueError("Group is already of boundary type.")

        return Group(self.geoms.boundary)

    @staticmethod
    def line(x0, y0, x1, y1):
        return Group(sh.geometry.MultiLineString([
            sh.geometry.LineString(((x0, y0), (x1, y1)))
        ]))

    @staticmethod
    def rect(start_x, start_y, width, height):
        return Group(sh.geometry.MultiPolygon([
                sh.geometry.box(start_x, start_y, start_x + width, start_y + height)
            ]))

    @staticmethod
    def rect_centered(x, y, width, height):
        return Group.rect(x - width / 2, y - height / 2, width, height)

    @staticmethod
    def from_geomarray(geomarray, geom_attributes_manager=None):
        flattened = flatten_geoms(geomarray)

        if len(flattened) == 0:
            return Group(geoms=None, geom_attributes_manager=geom_attributes_manager)
        elif flattened[0].type == "Polygon":
            return Group(sh.geometry.MultiPolygon([f for f in flattened if not f.is_empty]), geom_attributes_manager=geom_attributes_manager)
        elif flattened[0].type == "LineString":
            return Group(sh.geometry.MultiLineString([f for f in flattened if not f.is_empty]), geom_attributes_manager=geom_attributes_manager)
        else:
            raise ValueError(f"Unsupported geom type: {flattened[0]}")

    @staticmethod
    def arrange(groups, clearance):
        x_current = 0

        group_type = groups[0].type

        result = Group(group_type())
        for g in groups:
            result = result.add(g.anchor().translate(x_current, 0))
            x_current += g.bounds_width + clearance

        return result

    @staticmethod
    def from_text(text, font_face, font_size, font_slant=cairo.FontSlant.NORMAL, font_weight=cairo.FontWeight.NORMAL):
        # Annoyingly a value of int('inf'), 0, -1, or some other constant won't work here as for small dimensions
        # text seems to get cut off at arbitrary limits, so I just went with a "very big number".
        surface = cairo.SVGSurface(None, 2147483647, 2147483647)
        context = cairo.Context(surface)

        context.select_font_face(font_face, font_slant, font_weight)
        context.set_font_size(font_size)

        context.move_to(0, 0)
        context.text_path(text)

        path = context.copy_path_flat()

        polygons = []
        coord_stack = []

        for p in path:
            type = p[0]
            coords = p[1]

            if type == cairo.PathDataType.MOVE_TO:
                coord_stack.append(coords)
            elif type == cairo.PathDataType.LINE_TO:
                coord_stack.append(coords)
            elif type == cairo.PathDataType.CLOSE_PATH:
                next_polygon = sh.geometry.Polygon(coord_stack + [ coord_stack[0] ])

                polygons.append(next_polygon)
                coord_stack.clear()

        surface.finish()

        return Group.from_geomarray(polygons)
