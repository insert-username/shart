import unittest
from unittest.mock import Mock, MagicMock

import math

import shapely as sh
import shapely.geometry

import numpy as np
import numpy.testing

import shart
from shart.box import *


class TestMain(unittest.TestCase):

    def test_attribute(self):
        g = Group.rect(0, 0, 100, 100)
        self.assertEqual({}, {k: d for k, d in g.geom_attributes_manager.attributes})

        g = g.add_geom_attribute("attrib_key", "attrib_value")
        self.assertDictEqual({0: {"attrib_key": "attrib_value"}}, dict(g.geom_attributes_manager.attributes))

    def test_add_group_attributes(self):
        g0 = Group.rect(0, 0, 100, 100).add_geom_attribute("g0", "g0_val")
        g1 = Group.rect(10, 10, 80, 80).add_geom_attribute("g1", "g1_val")

        self.assertDictEqual(
            {0: {"g0": "g0_val"}, 1: {"g1": "g1_val"}},
            dict(g0.add(g1).geom_attributes_manager.attributes))

    def test_filter_group_attribute(self):
        g0 = Group.rect(0, 0, 100, 100).add_geom_attribute("g0", "g0_val")
        g1 = Group.rect(10, 10, 80, 80).add_geom_attribute("g1", "g1_val")

        # filter to select the second group
        combined_and_filtered = g0.add(g1).filter(lambda g: g.bounds_width == 80)
        self.assertDictEqual(
            {0: {"g1": "g1_val"}},
            dict(combined_and_filtered.geom_attributes_manager.attributes))

    def test_single_group_union_attributes(self):
        g0 = Group.rect(0, 0, 100, 100) \
            .add(Group.rect(50, 50, 100, 100)) \
            .add_geom_attribute("g0", "g0_val")

        g_union = g0.union()

        self.assertDictEqual(
            {0: {"g0": "g0_val"}},
            dict(g_union.geom_attributes_manager.attributes))

    def test_multiple_group_union_attributes(self):
        g0 = Group.rect(0, 0, 100, 100).add_geom_attribute("g0", "g0_val")
        g1 = Group.rect(10, 10, 80, 80).add_geom_attribute("g1", "g1_val")

        g_union = g0.union(g1)

        self.assertDictEqual(
            { 0: { "g0": "g0_val", "g1": "g1_val" } },
            dict(g_union.geom_attributes_manager.attributes))

    def test_multiple_group_union_key_collsion(self):
        g0 = Group.rect(0, 0, 100, 100).add_geom_attribute("g", "g0_val")
        g1 = Group.rect(10, 10, 80, 80).add_geom_attribute("g", "g1_val")

        g_union = g0.union(g1)

        self.assertDictEqual(
            {0: {"g": "g1_val"}},
            dict(g_union.geom_attributes_manager.attributes))

    def test_multiple_attributes(self):
        g0 = Group.rect(0, 0, 100, 100).add_geom_attribute("a", "aval").add_geom_attribute("b", "bval")

        self.assertDictEqual(
            {0: {"a": "aval", "b": "bval"}},
            dict(g0.geom_attributes_manager.attributes))

    def test_multiple_attributes_and_reassign(self):
        g0 = Group.rect(0, 0, 100, 100)\
            .add_geom_attribute("a", "aval")\
            .add_geom_attribute("b", "bval")\
            .add_geom_attribute("b", "newbval")

        self.assertDictEqual(
            {0: {"a": "aval", "b": "newbval"}},
            dict(g0.geom_attributes_manager.attributes))

