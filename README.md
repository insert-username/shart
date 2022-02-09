# SHapely Art Tools

Fluent api wrapper around shapely geometry library.

# Why
Shapely is a very powerful library with awesome features,
but I find its API to be a bit verbose at times. I created
this lib to make my life a bit easier creating laser cutter
art projects.

# Limitations
Since this lib is just a glorified wrapper class, it has the
same limitations shapely does. Namely it does not support
"true" curves (everything is a polygon). I get around this by
estimating the number of segments required for e.g. a circle
based on its size, but it's important to be aware that if you
create a tiny circle and scale it up 100 times it won't be
infinitely detailed. Same goes for any other curve objects.

# Install

Clone repo and run
```
./build-and-install.sh
```

Note you need the usual set of dependencies required when building pip packages.

# Example Use

Central class of the API is a Group, which is a collection of one or more
geometric objects (backed by a shapely MultiPolygon):

## You can render directly to SVG (Using PyCairo)

`svg_generator` is a lambda that accepts width/height arguments and provides
a cairo surface from which a render context can be created. Use your own
lambda for alternative outputs.

```
Group.circle(0, 0, 100).render(Group.svg_generator("doc/circle"))
```

![Generated SVG](./doc/circle.svg)

## Multiple shapes are allowed

```
Group.circle(0, 0, 100) \
    .add(Group.circle(0, 0, 50)) \
    .render(Group.svg_generator("doc/circle-add"))
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
    .render(Group.svg_generator("doc/circles"))

```

![Generated SVG](./doc/circles.svg)

## Using union()

```
outer_circle \
    .add(inner_circle.to(50, 0)) \
    .add(inner_circle.to(-50, 0)) \
    .union() \
    .render(Group.svg_generator("doc/circles-union"))
```

![Generated SVG](./doc/circles-union.svg)

## Boolean operations

```
center_rect = Group.rect_centered(0, 0, 100, 100)

spin_rects = Group.rect(0, -5, 100, 10)

spin_rects \
        .spin(0, 0, 20, should_rotate=True) \
        .difference(center_rect) \
        .union() \
        .render(Group.svg_generator("doc/boolean"))
```

![Generated SVG](./doc/boolean.svg)

## Using spin()

```
Group.rect_centered(50, 0, 10, 10) \
    .spin(0, 0, 10, should_rotate=True) \
    .render(Group.svg_generator("doc/rects"))
```

![Generated SVG](./doc/rects.svg)

## Using linarray()

Pass in a lambda which applies the desired transformation for a given increment

```
roup.rect_centered(0, 0, 10, 10) \
       .linarray(10,
               lambda i, g: g.to(i * 20, 0).rotate(i * 10, use_radians=False)) \
       .render(Group.svg_generator("doc/rects-linarray"))
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

