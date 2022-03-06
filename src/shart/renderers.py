import cairo

from defusedxml import ElementTree as etree
import shapely as sh
import shapely.validation
import shapely.geometry


class PrimitiveRenderer:

    def init_canvas(self):
        raise NotImplementedError()

    def start_path(self, x0, y0):
        raise NotImplementedError()

    def path_point(self, x0, y0):
        raise NotImplementedError()

    def path_move_to(self, x0, y0):
        raise NotImplementedError()

    def close_path(self, color=None, fill=False):
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
        self.context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)

    def start_path(self, x0, y0):
        self.context.new_path()
        self.context.move_to(x0, y0)

    def path_point(self, x0, y0):
        self.context.line_to(x0, y0)

    def path_move_to(self, x0, y0):
        self.context.move_to(x0, y0)

    def close_path(self, color=None, fill=False):
        if color is None:
            self.context.set_source_rgb(0, 0, 0)
        else:
            self.context.set_source_rgba(*color)

        if fill:
            self.context.fill()
        else:
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

    def _offset_coords(self, x, y):
        return self._x_offset + x, self._y_offset + y

    @staticmethod
    def _geom_attrs_to_named_args(geom_attributes):
        return {
            "color": geom_attributes.get("color", (0, 0, 0)),
            "fill": geom_attributes.get("fill", False)
        }

    def render(self, geometry, primitive_renderer, geom_attributes):
        if geometry.type == "LineString" or geometry.type == "LinearRing":
            self._render_linestring(geometry, primitive_renderer, geom_attributes)
        elif geometry.type == "Polygon":
            self._render_polygon(
                geometry.exterior,
                geometry.interiors,
                primitive_renderer, geom_attributes)
        elif geometry.type == "MultiPolygon":
            for g in geometry.geoms:
                self.render(g, primitive_renderer, geom_attributes)
        elif geometry.type == "MultiLineString":
            for linestring in geometry.geoms:
                self._render_linestring(linestring, primitive_renderer, geom_attributes)
        else:
            raise ValueError(f"Unsupported geometry type: {geometry.type}")

    def _render_polygon(self, linear_ring_exterior, linear_ring_interiors, primitive_renderer, geom_attributes):
        primitive_renderer.start_path(*self._offset_coords(*linear_ring_exterior.coords[0]))

        for c in linear_ring_exterior.coords[1:]:
            primitive_renderer.path_point(*self._offset_coords(*c))

        for interior_ring in linear_ring_interiors:
            if interior_ring.is_ccw == linear_ring_exterior.is_ccw:
                raise ValueError(f"Exterior ring cww({linear_ring_exterior.is_ccw}) does not differ from "
                                 f"interior ring ccw({interior_ring.is_ccw}). Coordinate orientation must differ "
                                 f"for rendering to work correctly.")

            primitive_renderer.path_move_to(*self._offset_coords(*interior_ring.coords[0]))
            for c in interior_ring.coords[1:]:
                primitive_renderer.path_point(*self._offset_coords(*c))

        primitive_renderer.close_path(**self._geom_attrs_to_named_args(geom_attributes))

    def _render_linestring(self, linestring, primitive_renderer, geom_attributes):
        primitive_renderer.start_path(*self._offset_coords(*linestring.coords[0]))

        for c in linestring.coords[1:]:
            primitive_renderer.path_point(c[0] + self._x_offset, c[1] + self._y_offset)

        primitive_renderer.close_path(**self._geom_attrs_to_named_args(geom_attributes))


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

        gm = group.geom_attributes_manager

        for index, geom in enumerate(group.geoms.geoms):
            attributes = gm.get_geom_attributes(index)
            geometry_renderer.render(geom, primitive_renderer, attributes)

        self._post_render_callback(geometry_renderer, primitive_renderer)

        primitive_renderer.finish_canvas()

        return group
