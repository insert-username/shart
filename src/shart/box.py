import math

from .group import Group


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
