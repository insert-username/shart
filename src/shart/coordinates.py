import math

import shapely as sh
import shapely.geometry

import numpy as np

from .group import Group


class Coordinates:

    def __init__(self, values):
        self.values = list(values)

    def offset(self, dx=0, dy=0):
        return Coordinates([ (c[0] + dx, c[1] + dy) for c in self.values ])

    def multiply(self, fx, fy=None):
        if fy is None:
            fy = fx

        return Coordinates([(c[0] * fx, c[1] * fy) for c in self.values])

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
    def polar(steps, fn=lambda theta: 1, theta_start=0, theta_stop=(math.pi * 2)):
        result = []
        halfpi = math.pi / 2
        for theta in np.linspace(theta_start, theta_stop, num=steps, endpoint=(theta_start % halfpi != theta_stop % halfpi)):
            hypot = fn(theta)
            result.append(
                    (hypot * math.cos(theta), hypot * math.sin(theta)))

        return Coordinates(result)
