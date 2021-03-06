#!/usr/bin/env python3

import math

import sys

import numpy as np
import shapely as sh
import shapely.geometry

from shart.box import BoxFace, FingerGenerator, SlotGenerator
from shart.coordinates import Coordinates
from shart.group import Group
from shart.line_generator import Turtle
from shart.renderers import RenderBuilder

print("Creating attributes #1")
c1 = Group.circle(0, 0, 100)\
    .add_geom_attribute("fill", True)\
    .add_geom_attribute("color", (1, 0, 0))
c2 = c1.translate(70, 0).add_geom_attribute("color", (0, 1, 0, 0.5))
c3 = c2.translate(70, 0).add_geom_attribute("color", (0, 0, 1, 0.75))
c1.add(c2).add(c3).border(20, 20).do(RenderBuilder().svg().file("doc/attributes-demo-1"))

print("Creating attributes #2")
Group.circle(0, 0, 100).difference(Group.circle(0, 0, 50)) \
    .add_geom_attribute("fill", True) \
    .add_geom_attribute("color", (1, 0, 0)) \
    .border(20, 20)\
    .do(RenderBuilder().svg().file("doc/attributes-demo-2"))

print("Creating circle")

# Single shape
Group.circle(0, 0, 100) \
    .do(RenderBuilder()
        .svg()
        .units_mm()
        .file("doc/circle"))

print("Creating circle-add")

# Multiple shapes are allowed
Group.circle(0, 0, 100) \
    .add(Group.circle(0, 0, 50)) \
    .do(RenderBuilder().svg().file("doc/circle-add"))

print("Creating circles")

# Group is immutable so you can easily perform multiple transformations using the same base group
outer_circle = Group.circle(0, 0, 100)

inner_circle = Group.circle(0, 0, 20)

outer_circle \
    .add(inner_circle.to(50, 0)) \
    .add(inner_circle.to(-50, 0)) \
    .do(RenderBuilder().svg().file("doc/circles"))

print("Creating circles-union")

# Using union()
outer_circle \
    .add(inner_circle.to(50, 0)) \
    .add(inner_circle.to(-50, 0)) \
    .union() \
    .do(RenderBuilder().svg().file("doc/circles-union"))

print("Creating line")
Group.line(0, 0, 30, 0)\
    .spin(0, 0, 10, geom_centroid=sh.geometry.Point(0, 0), should_rotate=True)\
    .do(RenderBuilder().svg().file("doc/line"))

print("Creating line w. buffer")
Group.line(0, 0, 50, 0)\
    .spin(0, 0, 10, geom_centroid=sh.geometry.Point(0, 0), should_rotate=True)\
    .do_and_add(lambda g: g.buffer(10).to_boundary())\
    .do(RenderBuilder().svg().file("doc/line-boundary"))

print("Creating boolean")

# Boolean operations

center_rect = Group.rect_centered(0, 0, 100, 100)

spin_rects = Group.rect(0, -5, 100, 10)

spin_rects \
        .spin(0, 0, 20, should_rotate=True) \
        .difference(center_rect) \
        .union() \
        .do(RenderBuilder().svg().file("doc/boolean"))

print("Turtle")
circ = Group.circle(0, 0, 120)
Turtle(origin=(0, 0), angle_rad=math.radians(-90))\
    .do(lambda t, i: t.move(3 * i).turn_deg(90), 50)\
    .to_group()\
    .intersection(circ)\
    .add(circ.to_boundary())\
    .border(10, 10)\
    .do(RenderBuilder().svg().file("doc/turtle"))

print("Creating rects")

# Using spin()
Group.rect_centered(50, 0, 10, 10) \
    .spin(0, 0, 10, should_rotate=True) \
    .do(RenderBuilder().svg().file("doc/rects"))


print("Creating rects-linarray")

# Using linarray()
Group.rect_centered(0, 0, 10, 10) \
       .linarray(10,
               lambda i, g: g.to(i * 20, 0).rotate(i * 10, use_radians=False)) \
       .do(RenderBuilder().svg().file("doc/rects-linarray"))


print("Creating hexagons-hard")

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
    .do(RenderBuilder().svg().file("doc/hexagons-hard"))


print("Creating hexagons")

# Creating hexagonal tiling, the easy way
Group() \
        .add_all(Group.circle(c[0], c[1], 4) for c in Coordinates.hex(17, 17, 10)) \
        .filter(lambda g: container.contains(g)) \
        .add(container) \
        .do(RenderBuilder().svg().file("doc/hexagons"))


print("Creating polar-w-boolean")

# Creating shapes from polar coordinates
flower = Coordinates.polar(300, lambda t: 10 + 150 * abs(math.cos(t * 3))).to_group()

hexagon = Coordinates.polar(6, lambda t: 2).to_group()
hexagons = Group().add_all(
    hexagon.to(c[0], c[1]) for c in Coordinates.hex_covering(4 * math.sqrt(4/3), flower, row_parity=True))

bars = Group() \
        .add_all(Group.rect_centered(0, c[1], 320, 20) for c in Coordinates.linear(10, dy=40, centered_on=(0, 0))) \
        .intersection(flower)

hexagons \
        .filter(lambda g: flower.covers(g)) \
        .filter(lambda g: not bars.intersects(g)) \
        .add(bars) \
        .add(
                flower.do_and_add(lambda f: f.buffer(10).add(f.buffer(15)))
                ) \
        .border(10, 10) \
        .do(RenderBuilder().svg().file("doc/polar-w-boolean"))


print("Creating recurse-single")


# Hey dawg I heard you like hey dawg I heard you like hey dawg I heard you like...
def get_fractal_visitor(i0, i1, angle=45, scale=0.8):

    def modifier(g):
        pa = g.geoms.geoms[0].boundary.coords[i0]
        pb = g.geoms.geoms[0].boundary.coords[i1]

        pab = tuple(np.subtract(pb, pa))

        subgroup = g.translate(pab[0], pab[1]) \
                .scale(scale, origin=pb) \
                .rotate(angle, origin=pb, use_radians=False)


        return [ subgroup ]

    return modifier


Group.rect(0, 0, 100, 100) \
    .recurse(get_fractal_visitor(-2, 1, angle=38, scale=0.8), 15) \
    .map_subgroups(lambda g: g.recurse(get_fractal_visitor(1, 3, angle=45, scale=0.6), 4)) \
    .map_subgroups(lambda g: g.recurse(get_fractal_visitor(-1, 2, angle=45, scale=0.5), 4)) \
    .border(20, 20) \
    .do(RenderBuilder().svg().file("doc/recurse-single"))


print("Creating recurse-tree")

def branching_fractal_visitor(g):
    scale = 0.5
    angle = 10

    top_right = g.geoms.geoms[0].boundary.coords[0]
    top_left = g.geoms.geoms[0].boundary.coords[-2]
    bottom_right = g.geoms.geoms[0].boundary.coords[1]
    bottom_left = g.geoms.geoms[0].boundary.coords[2]

    tl_br = tuple(np.subtract(bottom_right, top_left))
    tr_bl = tuple(np.subtract(bottom_left, top_right))

    subgroup1 = g.translate(tl_br[0], tl_br[1]) \
            .scale(scale, origin=bottom_right) \
            .rotate(angle, origin=bottom_right, use_radians=False)

    subgroup2 = g.translate(tr_bl[0], tr_bl[1]) \
            .scale(scale, origin=bottom_left) \
            .rotate(-angle, origin=bottom_left, use_radians=False)

    return [ subgroup1,  subgroup2 ]


Group.rect(0, 0, 100, 100) \
    .recurse(branching_fractal_visitor, 6) \
    .border(20, 20) \
    .do(RenderBuilder().svg().file("doc/recurse-tree"))

print("Creating Turtle fork")
forklength = lambda depth: max(0.0, 50 * math.pow(2, -depth))

Turtle(angle_rad=math.radians(-90)).move(100).fork(lambda d, instance: (
        instance().turn_deg(-50).move(forklength(d)),
        instance().turn_deg(-20).move(forklength(d)),
        instance().turn_deg(30).move(forklength(d))), 4)\
    .to_group()\
    .border(20, 20)\
    .do(RenderBuilder().svg().file("doc/turtle-fork"))

print("Creating finger-joint-phases")

def create_for_phase(phase):
    bf = BoxFace(sh.geometry.box(0, 0, 100, 20))
    bf.assign_edge(2, FingerGenerator.create_for_length(100, 5, True, 6.5, 1, 0.1, duty=0.5, phase=phase))
    bf.assign_edge(0, FingerGenerator.create_for_length(100, 5, False, 6.5, 1, 0.1, duty=0.5, phase=phase))

    return bf.generate_group()\
        .union()\
        .add(Group.from_text(f"Phase: {round(phase, 4)}", "Linux Libertine O", 10).translate(10, 15))


Group() \
    .add_all([create_for_phase(p).translate(0, i * 40) for i, p in enumerate(np.linspace(0, 1, 10, endpoint=True))]) \
    .border(10, 10) \
    .do(RenderBuilder().svg().file("doc/finger-joint-phases"))

print("Creating finger-joint")

fgen_male = FingerGenerator.create_for_length(100, 5, True, 6.5, 1, 0.1)
fgen_female = FingerGenerator.create_for_length(100, 5, False, 6.5, 1, 0.1)

bf = BoxFace(sh.geometry.box(0, 0, 100, 100))

# bottom
bf.assign_edge(2, fgen_male)

# top
bf.assign_edge(0, fgen_female)

# right
bf.assign_edge(3, fgen_female)

# left
bf.assign_edge(1, fgen_male)

bf.generate_group() \
    .union() \
    .do_and_add(lambda g: g.translate(121, 0)) \
    .do_and_add(lambda g: g.translate(0, 121)) \
    .add(fgen_male.get_slots(((50, 0), (50, 100))).do(lambda s: s.translate(-s.bounds_width / 2, 0))) \
    .border(20, 20) \
    .do(RenderBuilder().svg().file("doc/finger-joint"))

print("Creating non-group")

# Rendering non-group geoms
extra_geoms = [ sh.geometry.LineString([ ( 50 / math.sqrt(2), 50 / math.sqrt(2) ), ( 100, 100 ) ]) ]
Group.circle(0, 0, 100) \
    .add(Group.circle(0, 0, 50)) \
    .do(RenderBuilder()
        .svg()
        .file("doc/non-group")
        .post_render_callback(
            lambda geom_r, prim_r: [geom_r.render(eg, prim_r, {}) for eg in extra_geoms]))

print("Creating text")

# Creating geoms from text
Group.from_text("Hi world", "Linux Libertine O", 50) \
    .border(10, 10) \
    .do(RenderBuilder().svg().file("doc/text"))

print("Creating slot")

sf = SlotGenerator(1, 2)

a_profile = Group.rect(0, 0, 100, 50)\
    .union(sf.get_slot([(50, 25), (50, 75)], 10, is_hole=False))

b_profile = Group.rect(0, 52, 100, 50)\
    .difference(sf.get_slot([(50, 49), (50, 75)], 10, is_hole=True))

a_profile.add(b_profile)\
    .border(10, 10)\
    .do(RenderBuilder().svg().file("doc/slot"))

print("Creating dovetail")

sg = SlotGenerator(kerf=1, clearance=2)

# dovetails
dovetails = Group.from_geomarray([sh.geometry.Polygon([(0, 0), (1, 0), (1.5, 1), (-0.5, 1)])])\
    .scale(10, 10, origin=(0, 0))\
    .linarray(3, lambda i, g: g.to(15 + i * 30, 48, center=(0, 0)))

sheet_a = Group.rect(0, 0, 100, 50)
sheet_b = sheet_a\
    .translate(0, sheet_a.bounds_height)\
    .translate(0, sg.get_object_separation())  # add the offset required to mate the profiles with the desired clearance

sheet_a = sheet_a.add(sg.buffer_profile(dovetails, False)).union()
sheet_b = sheet_b.difference(sg.buffer_profile(dovetails, True))

Group.arrange([ sheet_a.add(sheet_b), sheet_a, sheet_b ], 10)\
    .border(10, 10)\
    .do(RenderBuilder().svg().file("doc/dovetail"))
