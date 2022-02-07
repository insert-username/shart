# SHapely Art Tools

Fluent api wrapper around shapely geometry library.

# Why
Shapely is a very powerful library with awesome features,
but I find its API to be a bit verbose at times. I created
this lib to make my life a bit easier creating laser cutter
art projects.

# Install

Clone repo and run
```
./build-and-install.sh
```

Note you need the usual set of dependencies required when building pip packages.

# Example Use

Central class of the API is a Group, which is a collection of one or more
geometric objects (backed by a shapely MultiPolygon):

## You can render directly to SVG

```
Group.circle(0, 0, 100).render(Group.svg_generator("doc/circle.svg"))
```

![Generated SVG](./doc/circle.svg)

## Multiple shapes are allowed

```
Group.circle(0, 0, 100) \
    .add(Group.circle(0, 0, 50)) \
    .render(Group.svg_generator("doc/circle-add.svg"))
```

![Generated SVG](./doc/circle-add.svg)

## Group is immutable so you can easily perform multiple transformations using the same base group

```
from shat import Group

outer_circle = Group.circle(0, 0, 100)

inner_circle = Group.circle(0, 0, 20)

outer_circle \
    .add(inner_circle.to(50, 0)) \
    .add(inner_circle.to(-50, 0)) \
    .render(Group.svg_generator("doc/circles.svg"))

```

![Generated SVG](./doc/circles.svg)

## Using union()

```
outer_circle \
    .add(inner_circle.to(50, 0)) \
    .add(inner_circle.to(-50, 0)) \
    .union() \
    .render(Group.svg_generator("doc/circles.svg"))
```

![Generated SVG](./doc/circles-union.svg)

## Using spin()

```
Group.rect_centered(50, 0, 10, 10) \
    .spin(0, 0, 10, should_rotate=True) \
    .render(Group.svg_generator("doc/rects.svg"))
```

![Generated SVG](./doc/rects.svg)

## Using linarray()

Pass in a lambda which applies the desired transformation for a given increment

```
roup.rect_centered(0, 0, 10, 10) \
       .linarray(10,
               lambda i, g: g.to(i * 20, 0).rotate(i * 10, use_radians=False)) \
       .render(Group.svg_generator("doc/rects-linarray.svg"))
```

![Generated SVG](./doc/rects-linarray.svg)

## Accessing the underlying MultiPolygon

Since the API will never give you everything you could possibly want to do,
You can just grab the underlying shapely MultiPolygon like so:

```
>>> from shat import Group
>>> my_group = Group.circle(0, 0, 10)
>>> type(my_group.geoms)
<class 'shapely.geometry.multipolygon.MultiPolygon'>
```

You can just create a new group from a MultiPolygon

```
my_group = Group(my_old_group.geoms)
```

