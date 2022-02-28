import cairo

from defusedxml import ElementTree as etree

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

    class SVGFileModifier:

        def __init__(self):
            self.lines = []

        def read(self):
            raise NotImplementedError()

        def write(self, content):
            self.lines.append(content)

        def get_modified_contents(self):
            document = ''.join(line.decode("utf-8") for line in self.lines)
            tree = etree.fromstring(document)

            groups = [g for g in tree if g.tag.endswith("}g")]

            if len(groups) != 1:
                raise ValueError("Output should consist of single group.")

            group_element = groups[0]
            group_element.attrib["id"] = "surface"

            return etree.tostring(tree, encoding="unicode")

    def __init__(self,
                 output_file_path,
                 width,
                 height,
                 fill_background=False,
                 svg_unit=cairo.SVGUnit.MM):
        self._output_file_path = output_file_path
        self._svg_file_modifier = SVGPrimitiveRenderer.SVGFileModifier()
        self._width = width
        self._height = height
        self._fill_background = fill_background
        self._svg_unit = svg_unit

        self.surface = None
        self.context = None

    def init_canvas(self):
        if self.surface is not None:
            raise RuntimeError("Surface already initialized.")

        self.surface = cairo.SVGSurface(self._svg_file_modifier, self._width, self._height)
        self.surface.set_document_unit(self._svg_unit)

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

        with open(self._output_file_path, "w") as f:
            f.write(self._svg_file_modifier.get_modified_contents())


class GeometryRenderer:

    def __init__(self, x_offset, y_offset):
        self._x_offset = x_offset
        self._y_offset = y_offset

    def render(self, geometry, primitive_renderer):
        if geometry.type == "LineString" or geometry.type == "LinearRing":
            self._render_linestring(geometry, primitive_renderer)
        elif geometry.type == "Polygon":
            self._render_linestring(geometry.exterior, primitive_renderer)
            for i in geometry.interiors:
                self.render(i, primitive_renderer)
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


class RenderBuilder:


    SVG_UNIT_MAP = {
        "user": cairo.SVGUnit.USER,
        "em": cairo.SVGUnit.EM,
        "ex": cairo.SVGUnit.EX,
        "px": cairo.SVGUnit.PX,
        "in": cairo.SVGUnit.IN,
        "inches": cairo.SVGUnit.IN,
        "cm": cairo.SVGUnit.CM,
        "mm": cairo.SVGUnit.MM,
        "pt": cairo.SVGUnit.PT,
        "pc": cairo.SVGUnit.PC,
        "percent": cairo.SVGUnit.PERCENT,
    }

    def __init__(self):
        self._fill_background = True
        self._filename = None
        self._append_dimensions_to_file_name = False
        self._output_format = None
        self._units = "pt"

        self._pre_render_callback = lambda geom_renderer, primitive_renderer: None
        self._post_render_callback = lambda geom_renderer, primitive_renderer: None

    def file(self, filename):
        self._filename = filename
        return self

    def svg(self):
        self._output_format = "svg"
        return self

    def units_mm(self):
        return self.units("mm")

    def units_inches(self):
        return self.units("inches")

    def units(self, units):
        self._units = units
        return self

    def append_dimensions_to_file_name(self, on=True):
        self._append_dimensions_to_file_name = on
        return self

    def fill_background(self, on=True):
        self._fill_background = on
        return self

    def pre_render_callback(self, pre_render_callback):
        self._pre_render_callback = pre_render_callback
        return self

    def post_render_callback(self, post_render_callback):
        self._post_render_callback = post_render_callback
        return self

    def _get_output_file_path(self, group):
        result = self._filename

        if self._append_dimensions_to_file_name:
            result = result + f"{group.bounds_width}_{group.bounds_height}"

        return result + "." + self._output_format

    def _get_render_units(self):
        if self._output_format == "svg":
            if self._units not in RenderBuilder.SVG_UNIT_MAP.keys():
                raise ValueError(f"Unknown unit for {self._output_format}: {self._units}")

            return RenderBuilder.SVG_UNIT_MAP[self._units]
        else:
            raise NotImplementedError()

    def _get_primitive_renderer(self, group):
        if self._output_format is None:
            raise ValueError("No output format specified")
        elif self._output_format == "svg":
            return SVGPrimitiveRenderer(
                self._get_output_file_path(group),
                group.bounds_width,
                group.bounds_height,
                self._fill_background,
                svg_unit=self._get_render_units())

    @staticmethod
    def _get_geom_renderer(group):
        return GeometryRenderer(-group.bounds_x, -group.bounds_y)

    def __call__(self, group):
        primitive_renderer = self._get_primitive_renderer(group)
        geometry_renderer = RenderBuilder._get_geom_renderer(group)

        primitive_renderer.init_canvas()

        self._pre_render_callback(geometry_renderer, primitive_renderer)

        for geom in group.geoms.geoms:
            geometry_renderer.render(geom, primitive_renderer)

        self._post_render_callback(geometry_renderer, primitive_renderer)

        primitive_renderer.finish_canvas()

        return group
