import shapely.geometry

import networkx as nx

from shapely.geometry import LineString, MultiLineString

import shart.renderers
from shart.group import Group

import random


class MazeGroupFactory:

    # returns the line group representing this
    # cell. Unit size.
    @staticmethod
    def get_cell_lines(maze, cell_index):
        cell_row, cell_column = maze.index_to_rc(cell_index)
        north = maze.rc_to_index(cell_row - 1, cell_column)
        south = maze.rc_to_index(cell_row + 1, cell_column)
        east = maze.rc_to_index(cell_row, cell_column + 1)
        west = maze.rc_to_index(cell_row, cell_column - 1)

        x0 = cell_column
        y0 = cell_row

        x1 = x0 + 1
        y1 = y0 + 1

        # north
        if not maze.graph.has_edge(cell_index, north):
            yield LineString([(x0, y0), (x1, y0)])

        # south
        if not maze.graph.has_edge(cell_index, south):
            yield LineString([(x0, y1), (x1, y1)])

        # west
        if not maze.graph.has_edge(cell_index, west):
            yield LineString([(x0, y0), (x0, y1)])

        # east
        if not maze.graph.has_edge(cell_index, east):
            yield LineString([(x1, y0), (x1, y1)])

    # returns resulting maze with each cell unit size
    @staticmethod
    def get_maze_group(maze):
        mls = MultiLineString([ls for ci in maze.graph.nodes for ls in MazeGroupFactory.get_cell_lines(maze, ci)])
        return Group(mls).union()


class Maze:

    def __init__(self, rows, columns):
        self.rows = rows
        self.columns = columns

        self.graph = nx.Graph()

        # Cell identifier is row * colcount + col
        self.graph.add_nodes_from(range(0, self.rows * self.columns))

    def rc_to_index(self, row, column):
        if row < 0 or row >= self.rows or column < 0 or column >= self.columns:
            return None

        return row * self.columns + column

    def index_to_rc(self, index):
        if index < 0 or index >= self.rows * self.columns:
            return None

        row = int(index / self.columns)
        column = index % self.columns

        return row, column

    def get_neighbors(self, row, column):
        north = self.rc_to_index(row + 1, column)
        south = self.rc_to_index(row - 1, column)
        east = self.rc_to_index(row, column + 1)
        west = self.rc_to_index(row, column - 1)

        for i in north, south, east, west:
            if self.graph.has_node(i):
                yield i

    def generate(self):

        maze_size = len(self.graph.nodes)

        start_cell = random.choice(list(self.graph.nodes.keys()))

        cell_stack = [start_cell]
        visited_cells = {start_cell}

        while len(visited_cells) < maze_size:
            if len(cell_stack) == 0:
                # fill any isolated islands
                cell_stack = [random.choice([c for c in self.graph.nodes.keys() if c not in visited_cells])]

            current_cell = cell_stack[-1]
            unvisited_neighbors = \
                [n for n in self.get_neighbors(*self.index_to_rc(current_cell)) if n not in visited_cells]

            if len(unvisited_neighbors) == 0:
                del cell_stack[-1]
            else:
                next_cell = random.choice(unvisited_neighbors)
                self.graph.add_edge(current_cell, next_cell)

                #print(f"{self.index_to_rc(current_cell)} ({current_cell}) ---> {self.index_to_rc(next_cell)} ({next_cell})")

                cell_stack.append(next_cell)
                visited_cells.add(next_cell)

