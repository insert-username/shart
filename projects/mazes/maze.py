from shart.group import Group

import shart.tools.maze as mz
from shart.renderers import RenderBuilder

import shapely as sh
import shapely.geometry
import shapely.validation

if __name__ == "__main__":
    # generate the flavor text
    # check which cells overlap it
    # create two separate mazes
    maze_height = 20
    maze_width = 50

    wall_thickness = 2
    text_margin = 10 #prevents walls from being completely flush to the text

    cell_scale = 20

        #.add(Group.from_text(f"You dingaling", "Linux Libertine O", 50).translate(0, 80))\
    text = Group.from_text(f"Bazinga!", "Linux Libertine O", 100) \
        .do(lambda g: Group(sh.validation.make_valid(g.geoms)))\
        .to((maze_width * cell_scale) / 2, (maze_height * cell_scale) / 2)

    negative_cells = []
    for column in range(0, maze_width):
        for row in range(0, maze_height):
            x0 = cell_scale * column
            y0 = cell_scale * row
            x1 = x0 + cell_scale
            y1 = y0 + cell_scale

            if sh.geometry.box(x0, y0, x1, y1).buffer(wall_thickness / 2 + text_margin).intersects(text.geoms):
                negative_cells.append((row, column))

    maze_positive = mz.Maze(maze_height, maze_width)

    for row, column in negative_cells:
        maze_positive.graph.remove_node(maze_positive.rc_to_index(row, column))

    print("Generating...")

    maze_positive.generate()

    print("Rendering...")

    maze_group = mz.MazeGroupFactory.get_maze_group(maze_positive)\
        .scale(cell_scale, cell_scale, origin=(0, 0))\
        .buffer(wall_thickness / 2)\
        .add(text)

    print("Saving...")

    maze_group.border(20, 20).do(RenderBuilder().svg().file("maze"))
