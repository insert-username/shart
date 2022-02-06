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

def draw_geom(c, geom, fill=False):
    line_points = geom.exterior.coords

    c.new_path()

    c.move_to(line_points[0][0], line_points[0][1])

    for i, p in enumerate(line_points):
        c.line_to(p[0], p[1])

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", metavar="OUTPUT")
    args = parser.parse_args()

    total_geoms = sh.geometry.MultiPolygon([])

    # center box
    total_geoms = append_geom(
            total_geoms,
            sh.geometry.box(0, 0, 20, 20))

    # demonstrate circular array
    total_geoms = append_geoms(
            total_geoms,
            circular_array(total_geoms.centroid, sh.geometry.Point(50, 0).buffer(8), 10))

    # move the total geoms to top left
    re_center = anchor_geom(total_geoms)
    total_geoms = re_center(total_geoms)

    print(f"Total geometry dimensions: {total_geoms.bounds[2]}, {total_geoms.bounds[3]}")

    surface = cairo.SVGSurface(args.output, total_geoms.bounds[2], total_geoms.bounds[3])
    c = cairo.Context(surface)
    c.set_line_width(2)
    c.set_line_join(cairo.LINE_JOIN_MITER)
    c.select_font_face("Linux Libertine O", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(6)

    # determine text size
    c.set_source_rgb(0.1, 0.1, 0.1)

    for g in total_geoms.geoms:
        draw_geom(c, g)

    surface.finish()
