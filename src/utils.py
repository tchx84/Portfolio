# utils.py
#
# Copyright 2020 Martin Abente Lahaye
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re


def find_new_name(directory, name):
    counter = 1

    while os.path.exists(os.path.join(directory, name)):
        components = re.split("(\(\d+\)$)", name)
        if len(components) > 1:
            name = "".join(components[:-2])

        name = f"{name}({counter})"
        counter += 1

    return name


def count(path):
    _count = 1

    if os.path.isdir(path):
        for directory, _, files in os.walk(path):
            _count += len(files)

    return _count


def flatten_walk(path):
    _paths = []

    def _callback(error):
        raise error

    if os.path.isdir(path):
        for directory, _, files in os.walk(path, topdown=False, onerror=_callback):
            for file in files:
                _paths += [os.path.join(directory, file)]
            _paths += [directory]
    else:
        _paths += [path]

    return _paths
