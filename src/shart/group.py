import math

import shapely as sh
import shapely.geometry
import shapely.ops
import shapely.affinity

import cairo

from .utils import *


class Group:

    def __init__(self, geoms=None):
        if geoms is None:
            self.geoms = sh.geometry.MultiPolygon([])
            self.type = sh.geometry.MultiPolygon
        else:
            if not isinstance(geoms, sh.geometry.MultiPolygon) and not isinstance(geoms, sh.geometry.MultiLineString):
                raise ValueError(f"Unsupported geom type: {geoms}")

            self.geoms = geoms
            self.type = type(geoms)

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
        return Group(anchor_geom(self.geoms)(self.geoms))

    def border(self, border_thickness, border_radius):
        border_geom = create_border_box(self.geoms, border_thickness, border_radius)

        if self.type == sh.geometry.MultiLineString:
            border_geom = border_geom.boundary

        return Group(
            self.type(
                [g for g in self.geoms.geoms] + [border_geom]
            ))

    def filter(self, predicate):
        return Group.from_geomarray([ g for g in self.geoms.geoms if predicate(Group.from_geomarray([g])) ])

    def do_and_add(self, modifier):
        return self.add(modifier(self))

    def do(self, modifier):
        return modifier(self)

    def map_subgroups(self, modifier):
        return Group().add_all([ modifier(Group.from_geomarray([g])) for g in self.geoms.geoms ])

    def add(self, geom):
        if isinstance(geom, Group):
            return self.add(geom.geoms)
        elif isinstance(geom, self.type):
            return Group.from_geomarray(
                list(self.geoms.geoms) + list(geom.geoms))
        else:
            hint = ""
            if self.type == sh.geometry.MultiLineString and type(geom) == sh.geometry.MultiPolygon:
                hint = "Did you mean to call to_boundary() ?"

            raise ValueError(f"Cannot add type {type(geom)} to group of type {self.type}. " + hint)

    def add_all(self, groups):
        new_geoms = [ g for g in self.geoms.geoms ]

        for group in groups:
            new_geoms += [ g for g in group.geoms.geoms ]

        return Group.from_geomarray(new_geoms)

    def intersection(self, group):
        return self.foreach_modify(lambda g: g.intersection(group.geoms))

    def difference(self, group):
        return self.foreach_modify(lambda g: g.difference(group.geoms))

    def union(self, geom=None):
        if geom is None:
            geoms = flatten_geoms([g for g in self.geoms.geoms])

            union = sh.ops.unary_union(geoms)

            return Group(ensure_multipolygon(union) if self.type == sh.geometry.MultiPolygon else ensure_multilinestring(union))

        elif isinstance(geom, Group):
            return self.union(geom.geoms)
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
        return Group(sh.affinity.translate(self.geoms, dx, dy))

    def scale(self, x, y=None, origin='center'):
        y = y or x

        return Group(sh.affinity.scale(self.geoms, xfact=x, yfact=y, origin=origin))

    def rotate(self, angle, use_radians=True, origin=None):
        if origin is None:
            origin = 'centroid'

        return Group(sh.affinity.rotate(self.geoms, angle, use_radians=use_radians, origin=origin))

    def spin(self, center_x, center_y, count, geom_centroid=None, should_rotate=False):

        polys = circular_array(
                sh.geometry.Point(center_x, center_y),
                self.geoms,
                count,
                geom_centroid,
                should_rotate)

        result = Group(self.type([]))
        for p in polys:
            result = result.add(p)

        return Group(result.geoms)

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

    # todo: deprecated
    def foreach_modify(self, modifier):
        return Group.from_geomarray([ modifier(g) for g in self.geoms.geoms ])

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
    def from_geomarray(geomarray):
        flattened = flatten_geoms(geomarray)

        if len(flattened) == 0:
            return Group()
        elif flattened[0].type == "Polygon":
            return Group(sh.geometry.MultiPolygon([f for f in flattened if not f.is_empty]))
        elif flattened[0].type == "LineString":
            return Group(sh.geometry.MultiLineString([f for f in flattened if not f.is_empty]))
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
    def from_text(text, font_face, font_size):
        surface = cairo.SVGSurface(None, 1, 1)
        context = cairo.Context(surface)

        context.select_font_face(font_face, cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
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
