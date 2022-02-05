#!/usr/bin/env bash

set -e

python3 -m build
pip install dist/shapely_art_tools-0.0.1.tar.gz
