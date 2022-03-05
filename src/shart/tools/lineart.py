
# returns a turtle concentrically spiralling inside the supplied rect
import math

import shapely.geometry

from shart.group import Group
from shart.line_generator import Turtle
from shart.renderers import RenderBuilder


def line_spiral(x0, y0, width, height, layers=3, start_angle=0):
    if start_angle not in [0, 90, 180, 270]:
        raise ValueError("Start angle must be a multiple of 90 less than 360")

    center_x = x0 + width / 2
    center_y = y0 + height / 2

    # thickness dictated by layer count
    spiral_step_x = width / (2 * layers)
    spiral_step_y = height / (2 * layers)

    turtle = Turtle((center_x, center_y), angle_rad=math.radians(start_angle))

    should_start_x = start_angle == 0 or start_angle == 180

    current_step_0 = 0
    current_step_1 = 0
    for i in range(0, layers * 2):
        turtle.move(current_step_0 + (spiral_step_x if should_start_x else spiral_step_y))
        turtle.turn_deg(90)
        turtle.move(current_step_1 + (spiral_step_y if should_start_x else spiral_step_x))
        turtle.turn_deg(90)
        current_step_0 += spiral_step_x if should_start_x else spiral_step_y
        current_step_1 += spiral_step_y if should_start_x else spiral_step_x

    return turtle


if __name__ == "__main__":

    Group.rect(0, 0, 200, 150)\
        .to_boundary()\
        .do_and_add(lambda g: line_spiral(g.bounds_x, g.bounds_y, g.bounds_width, g.bounds_height, layers=3, start_angle=270).to_group())\
        .border(20, 20)\
        .do(RenderBuilder().svg().file("spiral"))
