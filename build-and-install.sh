#!/usr/bin/env bash

set -e

python3 setup.py test
python3 -m build
pip install dist/shapely_art_tools-0.0.1.tar.gz
