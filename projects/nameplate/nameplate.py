import math

from shart.group import Group
from shart.renderers import RenderBuilder

import shapely as sh

if __name__ == "__main__":

    text = Group.from_text("Stella", "Linux Libertine O", 100).to(0, 0)

    margin = 2

    center_point = (
            text.bounds_mid_x + text.bounds_height / 2 + margin,
            text.bounds_mid_y + + text.bounds_width / 2 + margin
    )

    result = text.spin(center_point[0], center_point[1], 4, should_rotate=True)\
        .linarray(10, lambda i, g: g.scale(math.pow(0.5, i)).rotate(15 * i, origin=center_point, use_radians=False))

    name = result\
        .border(20, 20)\
        .do(RenderBuilder().svg().file("nameplate"))