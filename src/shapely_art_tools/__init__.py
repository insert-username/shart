#!/usr/bin/env python3

import argparse
import random

import shapely as sh
import shapely.geometry
import shapely.affinity
import shapely.ops

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

def anchor_geom(total_geoms):
    re_center_x = -total_geoms.bounds[0]
    re_center_y = -total_geoms.bounds[1]

    return lambda geom: sh.affinity.translate(geom, re_center_x, re_center_y)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", metavar="OUTPUT")
    args = parser.parse_args()

    total_geoms = sh.geometry.MultiPolygon([])

    # center hole
    total_geoms = append_geom(
            total_geoms,
            sh.geometry.box(0, 0, 50, 170))

    text_points = []
    for i in range(0, 10):
        y = i * 8 * 2 + 8
        height = 8 + (i - 5) * 0.1

        cutout = sh.geometry.box(0, y, 30, y + height)

        total_geoms = sh.geometry.MultiPolygon([total_geoms.difference(cutout)])

        text_points.append((sh.geometry.Point( 31, y), height))

    # move the total geoms to top left
    re_center = anchor_geom(total_geoms)
    total_geoms = re_center(total_geoms)
    text_points = [ (re_center(p), h) for p, h in text_points ]

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

    for p, h in text_points:
        c.move_to(p.x, p.y + 3 * h / 4)
        c.show_text(f"{h} mm")

    surface.finish()
