import cairo


class PrimitiveRenderer:

    def init_canvas(self):
        raise NotImplementedError()

    def start_line(self, x0, y0):
        raise NotImplementedError()

    def line_point(self, x0, y0):
        raise NotImplementedError()

    def finish_line(self):
        raise NotImplementedError()

    def finish_canvas(self):
        raise NotImplementedError()


class SVGPrimitiveRenderer(PrimitiveRenderer):

    def __init__(self, output_file_path, width, height, fill_background=False, append_dimension_to_file_path=False):
        self._output_file_path = output_file_path +\
            (f"{width}_{height}.svg" if append_dimension_to_file_path else ".svg")

        self._width = width
        self._height = height
        self._fill_background = fill_background

        self.surface = None
        self.context = None

    def init_canvas(self):
        if self.surface is not None:
            raise RuntimeError("Surface already initialized.")

        self.surface = cairo.SVGSurface(self._output_file_path, self._width, self._height)
        self.context = cairo.Context(self.surface)

        if self._fill_background:
            self.context.set_source_rgb(1, 1, 1)
            self.context.rectangle(0, 0, self._width, self._height)
            self.context.fill()

        self.context.set_line_width(1)
        self.context.set_line_join(cairo.LINE_JOIN_MITER)
        self.context.set_source_rgb(0, 0, 0)

    def start_line(self, x0, y0):
        self.context.new_path()
        self.context.move_to(x0, y0)

    def line_point(self, x0, y0):
        self.context.line_to(x0, y0)

    def finish_line(self):
        self.context.stroke()
        self.context.close_path()

    def finish_canvas(self):
        if self.surface is None:
            raise RuntimeError("Surface already completed.")

        self.surface.finish()


class GeometryRenderer:

    def __init__(self, x_offset, y_offset):
        self._x_offset = x_offset
        self._y_offset = y_offset

    def render(self, geometry, primitive_renderer):
        if geometry.type == "LineString":
            self._render_linestring(geometry, primitive_renderer)
        elif geometry.type == "Polygon":
            self._render_linestring(geometry.exterior, primitive_renderer)
        elif geometry.type == "MultiLineString":
            for linestring in geometry.geoms:
                self._render_linestring(linestring, primitive_renderer)
        else:
            raise ValueError(f"Unsupported geometry type: {geometry.type}")

    def _render_linestring(self, linestring, primitive_renderer):
        start_coord = linestring.coords[0]

        primitive_renderer.start_line(start_coord[0] + self._x_offset, start_coord[1] + self._y_offset)

        for c in linestring.coords[1:]:
            primitive_renderer.line_point(c[0] + self._x_offset, c[1] + self._y_offset)

        primitive_renderer.finish_line()


class GroupRenderer:

    @staticmethod
    def render_svg(group,
                   output_file_name,
                   fill_background=False,
                   append_dimension_to_filename=False,
                   pre_render=lambda geom_r, prim_r: None,
                   post_render=lambda geom_r, prim_r: None):

        primitive_renderer = SVGPrimitiveRenderer(
            output_file_name,
            group.bounds_width,
            group.bounds_height,
            fill_background,
            append_dimension_to_filename)

        primitive_renderer.init_canvas()

        geom_renderer = GeometryRenderer(-group.bounds_x, -group.bounds_y)

        pre_render(geom_renderer, primitive_renderer)

        for geom in group.geoms.geoms:
            geom_renderer.render(geom, primitive_renderer)

        post_render(geom_renderer, primitive_renderer)

        primitive_renderer.finish_canvas()
