#!/usr/bin/env python3

import argparse
import random

import shapely as sh
import shapely.geometry
import shapely.affinity
import shapely.ops

import numpy as np

import math
import random
import cairo


def draw_geom(c, geom, fill=False, dx=0, dy=0):
    if geom.type == "Polygon":
        _draw_line(c, geom.exterior.coords, fill, dx, dy)
    elif geom.type == "LineString":
        _draw_line(c, geom.coords, fill, dx, dy)
    elif geom.type == "MultiLineString":
        for g in geom.geoms:
            draw_geom(c, g, fill, dx, dy)
    else:
        raise ValueError(f"Unsupported geom type: {geom.type}")


def _draw_line(c, line_points, fill=False, dx=0, dy=0):
    if len(line_points) == 0:
        return

    c.new_path()

    c.move_to(line_points[0][0] + dx, line_points[0][1] + dy)

    for i, p in enumerate(line_points):
        c.line_to(p[0] + dx, p[1] + dy)

    if fill:
        c.fill()
    else:
        c.stroke()

    c.close_path()

def create_border_box(geom, border_thickness, border_radius):
    b = geom.bounds

    result = sh.geometry.box(
            b[0] - border_thickness + border_radius,
            b[1] - border_thickness + border_radius,
            b[2] + border_thickness - border_radius,
            b[3] + border_thickness - border_radius).buffer(border_radius)

    return result

def append_geom(total_geoms, geom):
    return sh.geometry.MultiPolygon(
            [ g for g in total_geoms.geoms ] + [ geom ])

def append_geoms(total_geoms, geoms):
    return sh.geometry.MultiPolygon(
            [ g for g in total_geoms.geoms ] + geoms)

def anchor_geom(total_geoms):
    re_center_x = -total_geoms.bounds[0]
    re_center_y = -total_geoms.bounds[1]

    return lambda geom: sh.affinity.translate(geom, re_center_x, re_center_y)

# generate circular array coordinates
def circular_array_coords(radius, count):
    return [ (radius * math.cos(a), radius * math.sin(a), a) for a in np.linspace(0, 2 * math.pi, count + 1) ][0:-1]

# duplicate geom in circular array
def circular_array(center_point, geom, count, geom_centroid=None, should_rotate=False):
    if geom_centroid is None:
        geom_centroid = geom.centroid

    r = math.hypot(geom.centroid.x - center_point.x, geom.centroid.y - center_point.y)

    coords = circular_array_coords(r, count)

    result = []

    for coord in coords:
        translation_x = center_point.x + coord[0] - geom_centroid.x
        translation_y = center_point.y + coord[1] - geom_centroid.y
        instance = sh.affinity.translate(geom, translation_x, translation_y)
        if should_rotate:
            instance = sh.affinity.rotate(instance, coord[2], use_radians=True)

        result.append(instance)

    return result

def flatten_polygons(polygons):
    result = []

    for p in polygons:
        if p.type == "MultiPolygon":
            result += flatten_polygons([ g for g in p.geoms ])
        else:
            result.append(p)

    return result

def ensure_multipolygon(p):
    if p.type == "MultiPolygon":
        return p
    else:
        return sh.geometry.MultiPolygon([ p ])

class Group:

    def __init__(self, geoms=None):
        self.geoms = geoms or sh.geometry.MultiPolygon([])

        if isinstance(self.geoms, Group):
            raise ValueError()

    @property
    def bounds_width(self):
        return self.geoms.bounds[2] - self.geoms.bounds[0]

    @property
    def bounds_height(self):
        return self.geoms.bounds[3] - self.geoms.bounds[1]

    def anchor(self):
        return Group(anchor_geom(self.geoms)(self.geoms))

    def border(self, border_thickness, border_radius):
        return Group(
                sh.geometry.MultiPolygon(
                        [ g for g in self.geoms.geoms ] + \
                        [ create_border_box(self.geoms, border_thickness, border_radius) ]
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
        elif isinstance(geom, sh.geometry.base.BaseGeometry):
            if geom.type == "MultiPolygon":
                return Group(
                    sh.geometry.MultiPolygon(
                            [g for g in self.geoms.geoms] +
                            [g for g in geom.geoms]
                        ))
            else:
                return Group(
                    sh.geometry.MultiPolygon(
                            [g for g in self.geoms.geoms] +
                            [ geom ]
                        ))
        else:
            raise ValueError()

    def add_all(self, groups):
        new_geoms = [ g for g in self.geoms.geoms ]

        for group in groups:
            new_geoms += [ g for g in group.geoms.geoms ]

        return Group.from_geomarray(new_geoms)

    def intersection(self, geom):
        return self.foreach_modify(lambda g: g.intersection(geom.geoms))

    def difference(self, geom):
        return self.foreach_modify(lambda g: g.difference(geom.geoms))

    def union(self, geom=None):
        if geom is None:
            polygons = flatten_polygons([ g for g in self.geoms.geoms ])

            union = sh.ops.unary_union(polygons)

            return Group(ensure_multipolygon(union))

        elif isinstance(geom, Group):
            return self.union(geom.geoms)
        elif geom.type == "MultiPolygon":
            subgeoms = [ g for g in geom.geoms ]

            if len(subgeoms) != 1:
                raise ValueError()

            return self.union(subgeoms[0])
        else:
            return Group(
                    sh.geometry.MultiPolygon([ g.union(geom) for g in self.geoms.geoms  ])
                    )

    def to(self, x_coord, y_coord, center=(None, None)):

        # if the user does not define a center, use the
        # geometric centroid
        cx = center[0] or self.geoms.centroid.x
        cy = center[1] or self.geoms.centroid.y

        dx = x_coord - cx
        dy = y_coord - cx

        return Group(sh.affinity.translate(self.geoms, dx, dy))

    def buffer(self, amount, resolution=16):
        return Group.from_geomarray([self.geoms.buffer(amount, resolution)])

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

        result = self
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

    def render(self, surface_generator, geom_modifier=lambda g: g):

        # most rendering surfaces require 0, 0 as
        # an origin point so reset to origin
        render_offsets = (
            -self.geoms.bounds[0],
            -self.geoms.bounds[1]
        )

        surface = surface_generator(self.geoms.bounds[2] - self.geoms.bounds[0], self.geoms.bounds[3] - self.geoms.bounds[1])

        c = cairo.Context(surface)
        c.set_line_width(1)
        c.set_line_join(cairo.LINE_JOIN_MITER)
        #c.select_font_face("Linux Libertine O", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        #c.set_font_size(6)
        c.set_source_rgb(0, 0, 0)

        to_render = geom_modifier(self.geoms.geoms)

        for g in to_render:
            draw_geom(c, g, dx=render_offsets[0], dy=render_offsets[1])

        surface.finish()

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


    @staticmethod
    def rect(start_x, start_y, width, height):
        return Group(sh.geometry.MultiPolygon([
                sh.geometry.box(start_x, start_y, start_x + width, start_y + height)
            ]))

    @staticmethod
    def rect_centered(x, y, width, height):
        return Group.rect(x - width / 2, y - height / 2, width, height)

    @staticmethod
    def svg_generator(name, append_dimension_info=False, fill_background=False):
        name_modifier = lambda width, height: f"{name}_{width}_{height}.svg" if append_dimension_info else f"{name}.svg"

        def prepare_svg_surface(width, height):
            output_name = f"{name}_{width}_{height}.svg" if append_dimension_info else f"{name}.svg"

            result = cairo.SVGSurface(output_name, width, height)

            if fill_background:
                c = cairo.Context(result)
                c.set_source_rgb(1, 1, 1)
                c.rectangle(0, 0, width, height)
                c.fill()

            return result

        return prepare_svg_surface

    @staticmethod
    def from_geomarray(geomarray):
        return Group(sh.geometry.MultiPolygon(flatten_polygons(geomarray)))

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

class Coordinates:

    def __init__(self, values):
        self.values = list(values)


    def offset(self, dx=0, dy=0):
        return Coordinates([ (c[0] + dx, c[1] + dy) for c in self.values ])

    def __iter__(self):
        return self.values.__iter__()

    def to_polygon(self):
        points = [ c for c in self.values ]
        return sh.geometry.Polygon(points)

    def to_group(self):
        return Group.from_geomarray([ self.to_polygon() ])

    @staticmethod
    def linear(count, dx=0, dy=0, centered_on=None):
        x0 = 0
        y0 = 0

        if centered_on is not None:
            x0 = - (dx * (count - 1)) / 2 + centered_on[0]
            y0 = - (dy * (count - 1)) / 2 + centered_on[1]

        return Coordinates([ (x0 + dx * i, y0 + dy * i) for i in range(0, count) ])

    @staticmethod
    def hex_covering(lattice_spacing, group, row_parity=None, column_parity=None):
        x0 = group.geoms.bounds[0]
        y0 = group.geoms.bounds[1]
        x1 = group.geoms.bounds[2]
        y1 = group.geoms.bounds[3]

        width = x1 - x0
        height = y1 - y0

        mid_x = x0 + 0.5 * width
        mid_y = y0 + 0.5 * height

        row_spacing = math.sqrt(3/4) * lattice_spacing

        column_count = math.ceil(width / lattice_spacing)
        if column_parity is not None:
            if (column_count % 2 == 0) != column_parity:
                column_count += 1

        row_count = math.ceil(height / row_spacing)
        if row_parity is not None:
            if (row_count % 2 == 0) != row_parity:
                row_count += 1

        return Coordinates.hex(
                column_count,
                row_count,
                lattice_spacing,
                centered_on=(mid_x, mid_y))


    @staticmethod
    def hex(columns, rows, lattice_spacing, centered_on=None):
        offs_x = 0
        offs_y = 0

        column_spacing = lattice_spacing
        row_spacing = math.sqrt(3/4) * lattice_spacing

        if centered_on is not None:
            offs_x = -((columns - 1) * lattice_spacing) / 2 + centered_on[0]
            offs_y = -((rows - 1) * row_spacing) / 2 + centered_on[1]

        for row in range(0, rows):
            col_count = columns if row % 2 == 0 else columns - 1
            col_start = 0 if row % 2 == 0 else lattice_spacing / 2

            for col in range(0, col_count):
                yield((col * column_spacing + col_start + offs_x, row * row_spacing + offs_y))

    @staticmethod
    def polar(steps, fn=lambda theta: 1):
        result = []
        for theta in np.linspace(0, math.pi * 2, num=steps, endpoint=False):
            hypot = fn(theta)
            result.append(
                    (hypot * math.cos(theta), hypot * math.sin(theta)))

        return Coordinates(result)


class BoxFace:

    def __init__(self, polygon):
        if polygon.type != "Polygon":
            raise ValueError("")

        self._polygon = polygon
        self._finger_generators = {}

    def assign_edge(self, edge_index, finger_generator):
        if edge_index in self._finger_generators:
            raise ValueError("Face already assigned.")

        self._finger_generators[edge_index] = finger_generator

    def generate_group(self):
        result = Group.from_geomarray([ self._polygon ])

        for index, edge in enumerate(self.edges):
            finger_generator = self._finger_generators.get(index, None)

            if finger_generator is not None:
                result = result.add(finger_generator.get_fingers(edge))

        return result

    @property
    def edges(self):
        coords = self._polygon.exterior.coords
        if self._polygon.exterior.is_ccw:
            coords = list(reversed(coords))
        else:
            coords = list(coords)

        return [ (coords[i], coords[i + 1]) for i in range(0, len(coords) - 1) ]


# handles splitting of a range into predefined segments
class IntervalCalculator:

    def __init__(self, period, duty, phase):
        self._period = period
        self._duty = duty
        self._phase = phase

    def get_intervals(self, range):
        wave_start = -(1 - self._phase) * self._period

        result = []

        while wave_start < range:
            turning_point = wave_start + self._period * self._duty
            next_wave_start = wave_start + self._period

            # don't include a full wavelength before the start
            if next_wave_start > 0:
                result.append(
                    ((wave_start, turning_point), (turning_point, next_wave_start)))

            wave_start = next_wave_start

        return result


class FingerGenerator:

    def __init__(self, interval_calculator, is_male, width, kerf, clearance):
        self._interval_calculator = interval_calculator

        self._is_male = is_male
        self.width = width
        self.kerf = kerf
        self.clearance = clearance

    @staticmethod
    def create_for_length(length, fingers, is_male, material_width, kerf, clearance, duty=0.5, phase=0.5):
        period = length / (fingers - 0.5)

        return FingerGenerator(IntervalCalculator(period, duty, phase), is_male, material_width, kerf, clearance)

    # returns a group representing
    # the fingers to be attached
    def get_fingers(self, edge):
        p0 = edge[0]
        p1 = edge[1]

        dx = p0[0] - p1[0]
        dy = p0[1] - p1[1]

        edge_length = math.hypot(dx, dy)

        result = Group()

        intervals = self._interval_calculator.get_intervals(edge_length)
        for interval in intervals:
            rect_interval = interval[0] if self._is_male else interval[1]

            box_start = rect_interval[0] - self.kerf / 2 + self.clearance / 2
            box_end = rect_interval[1] + self.kerf / 2 - self.clearance / 2

            box_start = max(0, box_start)
            box_end = min(edge_length, box_end)

            if not self._is_male:
                box_end_new = edge_length - box_start
                box_start_new = edge_length - box_end

                box_start = box_start_new
                box_end = box_end_new

            box_length = box_end - box_start

            if box_length > self.kerf:
                result = result.add(Group.rect(
                    box_start,
                    0,
                    box_length,
                    -self.width - self.kerf / 2))

        return result.translate(p1[0], p1[1]) \
            .rotate(math.atan2(dy, dx), origin=p1)

    def get_slots(self, edge):
        p0 = edge[0]
        p1 = edge[1]

        dx = p0[0] - p1[0]
        dy = p0[1] - p1[1]

        edge_length = math.hypot(dx, dy)

        result = Group()

        intervals = self._interval_calculator.get_intervals(edge_length)
        for interval in intervals:
            rect_interval = interval[0] if self._is_male else interval[1]

            slot_start = rect_interval[0] + self.kerf / 2 - self.clearance / 2
            slot_end = rect_interval[1] - self.kerf / 2 + self.clearance / 2

            slot_start = max(0, slot_start)
            slot_end = min(edge_length, slot_end)

            if not self._is_male:
                slot_end_new = edge_length - slot_start
                slot_start_new = edge_length - slot_end

                slot_start = slot_start_new
                slot_end = slot_end_new

            slot_length = slot_end - slot_start

            if slot_length > self.kerf:
                slot_width = self.width - self.kerf + self.clearance

                result = result.add(Group.rect(
                    slot_start,
                    0,
                    slot_length,
                    slot_width))

        return result.translate(p1[0], p1[1]) \
            .rotate(math.atan2(dy, dx), origin=p1)
