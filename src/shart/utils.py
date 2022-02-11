import shapely as sh
import shapely.geometry
import shapely.affinity

import numpy as np

import math


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
