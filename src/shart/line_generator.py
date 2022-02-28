import math
from inspect import signature

import shapely as sh
import shapely.geometry

from shart.group import Group


class Turtle:

    def __init__(self, origin=(0, 0), angle_rad=0):
        self._current_position = origin
        self._current_angle_rad = angle_rad

        self._coords = [[ origin ]]

    @property
    def current_x(self):
        return self._current_position[0]

    @property
    def current_y(self):
        return self._current_position[1]

    def do(self, consumer, iterations=1):
        for i in range(0, iterations):
            consumer(self, i)

        return self

    def fork(self, forker, depth):
        def instancer():
            return Turtle(origin=self._current_position, angle_rad=self._current_angle_rad)

        inputs = forker(0, instancer)
        pending_forks = inputs

        current_depth = 1
        while True:
            for p in pending_forks:
                self._coords = p._coords + self._coords

            if current_depth > depth:
                return self

            new_pending_forks = []
            for p in pending_forks:
                def instancer():
                    return Turtle(origin=p._current_position, angle_rad=p._current_angle_rad)

                forked = forker(current_depth, instancer)
                new_pending_forks += forked

            current_depth += 1
            pending_forks = new_pending_forks

    def to_multilinestring(self):
        lines = [sh.geometry.LineString(l) for l in self._coords if len(l) > 1]
        return shapely.geometry.MultiLineString(lines)

    def to_group(self):
        return Group(self.to_multilinestring())

    def _is_pen_up(self):
        return len(self._coords[-1]) == 0

    def to(self, x, y):
        self._current_position = (x, y)

        if not self._is_pen_up():
            self._coords[-1].append(self._current_position)

        return self

    def move(self, amount):
        dx = math.cos(self._current_angle_rad) * amount
        dy = math.sin(self._current_angle_rad) * amount

        self.to(self._current_position[0] + dx, self._current_position[1] + dy)

        return self

    def turn_to_deg(self, angle_deg):
        self._current_angle_rad = math.radians(angle_deg)
        return self

    def turn_to_rad(self, angle_rad):
        self._current_angle_rad = angle_rad
        return self

    def turn_deg(self, angle_deg):
        self._current_angle_rad += math.radians(angle_deg)

        return self

    def turn_rad(self, angle_rad):
        self._current_angle_rad += angle_rad

        return self

    def pen_up(self, ignore_redundant=False):
        if self._is_pen_up():
            if ignore_redundant:
                return
            else:
                raise ValueError("Pen already up.")

        # starts a new line
        self._coords.append([])

        return self

    def pen_down(self, ignore_redundant=False):
        if not self._is_pen_up():
            if ignore_redundant:
                return
            else:
                raise ValueError("Pen already down.")

        self._coords.append([self._current_position])

        return self
