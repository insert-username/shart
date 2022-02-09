#!/usr/bin/env python3

import math

import itertools

from shat import Group
from shat import Coordinates

# Single shape
Group.circle(0, 0, 100).render(Group.svg_generator("doc/circle", fill_background=True))


# Multiple shapes are allowed
Group.circle(0, 0, 100) \
    .add(Group.circle(0, 0, 50)) \
    .render(Group.svg_generator("doc/circle-add", fill_background=True))


# Group is immutable so you can easily perform multiple transformations using the same base group
outer_circle = Group.circle(0, 0, 100)

inner_circle = Group.circle(0, 0, 20)

outer_circle \
    .add(inner_circle.to(50, 0)) \
    .add(inner_circle.to(-50, 0)) \
    .render(Group.svg_generator("doc/circles", fill_background=True))


# Using union()
outer_circle \
    .add(inner_circle.to(50, 0)) \
    .add(inner_circle.to(-50, 0)) \
    .union() \
    .render(Group.svg_generator("doc/circles-union", fill_background=True))


# Boolean operations

center_rect = Group.rect_centered(0, 0, 100, 100)

spin_rects = Group.rect(0, -5, 100, 10)

spin_rects \
        .spin(0, 0, 20, should_rotate=True) \
        .difference(center_rect) \
        .union() \
        .render(Group.svg_generator("doc/boolean", fill_background=True))


# Using spin()
Group.rect_centered(50, 0, 10, 10) \
    .spin(0, 0, 10, should_rotate=True) \
    .render(Group.svg_generator("doc/rects", fill_background=True))


# Using linarray()
Group.rect_centered(0, 0, 10, 10) \
       .linarray(10,
               lambda i, g: g.to(i * 20, 0).rotate(i * 10, use_radians=False)) \
       .render(Group.svg_generator("doc/rects-linarray", fill_background=True))


# Creating hexagonal tiling
lattice_spacing = 10

row_count = 17
col_count = 17

def gen_row(row_number, g):
    num_cols = col_count if row_number % 2 == 0 else col_count - 1

    row_y = row_number * math.sqrt(3 / 4) * lattice_spacing
    col_x = 0 if row_number % 2 == 0 else lattice_spacing / 2

    # create the first row element
    row_start = g.translate(col_x, row_y)

    # fill in the remainder of the row
    return row_start.linarray(
            num_cols,
            lambda i, g: g.translate(i * lattice_spacing, 0))

lattice = Group.circle(0, 0, 4).linarray(row_count, gen_row)

container = Group.circle(70, 70, 140)

lattice.filter(lambda g: container.contains(g)) \
    .add(container) \
    .render(Group.svg_generator("doc/hexagons-hard", fill_background=True))

# Creating hexagonal tiling, the easy way
Group() \
        .add_all(Group.circle(c[0], c[1], 4) for c in Coordinates.hex(17, 17, 10)) \
        .filter(lambda g: container.contains(g)) \
        .add(container) \
        .render(Group.svg_generator("doc/hexagons", fill_background=True))
