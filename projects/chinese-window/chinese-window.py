#!/usr/bin/env python3
import math

from random import random, uniform, randint

import random

import shapely as sh
import shapely.geometry
from shart.coordinates import Coordinates
from shart.group import Group
from shart.line_generator import Turtle
from shart.renderers import RenderBuilder

import argparse


def generate_window():
    circ_main = Group.circle(0, 0, 300)
    circ_inner = circ_main.buffer(-random.uniform(15, 25))

    rect_horiz = Group.rect_centered(0, 0, circ_main.bounds_width, random.uniform(0, 50))
    rect_vert = rect_horiz.rotate(90, use_radians=False, origin=(0, 0))

    rect_center = Group.rect_centered(0, 0, random.uniform(60, 90), random.uniform(60, 90))

    spiral = Turtle(origin=(circ_inner.geoms.centroid.x, circ_inner.geoms.bounds[3])).pen_up()

    # Creates the arc segment starting the spiral
    for c in Coordinates.polar(
            20,
            theta_start=math.radians(90),
            theta_stop=math.radians(180 - random.uniform(10, 20))).multiply(circ_inner.bounds_width / 2):
        spiral.to(c[0], c[1])
        spiral.pen_down(ignore_redundant=True)

    spiral.turn_to_deg(0)
    spiral.to(-circ_inner.bounds_width / 5, spiral.current_y)
    spiral_max = random.uniform(30, 50)
    spiral_spacing = random.uniform(5, 15)
    spiral.do(lambda t, i: t.turn_deg(90).move(spiral_max - i * spiral_spacing), 4)
    spiral = spiral.to_group()

    window_vector = circ_main\
        .difference(rect_vert)\
        .difference(rect_horiz) \
        .difference(rect_center)\
        .intersection(Group.rect(0, 0, -500, 500))\
        .do(lambda g: g.to_boundary().add(spiral.intersection(g)))

    for i in range(0, randint(1, 3)):
        window_vector = window_vector.add(Group.line(0, 0, -random.uniform(100, 400), 300).intersection(circ_main).difference(circ_inner))

    for i in range(0, randint(0, 3)):
        h_pos0 = -random.uniform(40, 70)
        window_vector = window_vector.add(Group.line(h_pos0, spiral.bounds_y, h_pos0, rect_horiz.bounds_y + rect_horiz.bounds_height))

    for i in range(0, randint(0, 3)):
        v_pos0 = -random.uniform(50, 100)
        window_vector = window_vector.add(Group.line(rect_vert.bounds_x, v_pos0, 0, v_pos0))

    window_vector = window_vector\
        .do_and_add(lambda g: g.scale(-1, 1, origin=(0, 0)))\
        .do_and_add(lambda g: g.scale(1, -1, origin=(0, 0)))

    window_outer = window_vector.buffer(3, join_style=shapely.geometry.JOIN_STYLE.mitre, cap_style=shapely.geometry.CAP_STYLE.flat)
    window_inner = window_vector.scale(0.2)
    return window_outer.to_boundary().add(window_inner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a chinese style window.")
    parser.add_argument("output_file_name")
    parser.add_argument("count", nargs="?", type=int, default=1)
    parser.add_argument("seed", nargs="?", type=int, default=None)

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    windows = Group.arrange([ generate_window() for i in range(0, args.count) ], 30)

    print("Rendering...")
    windows\
        .border(20, 20)\
        .do(RenderBuilder().svg().file(args.output_file_name))

