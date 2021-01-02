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


def flatten_walk(path, topdown=True):
    paths = []

    if os.path.isdir(path):
        for directory, _, files in os.walk(path, topdown=topdown):
            if topdown is True:
                paths.append(directory)
            for file in files:
                paths.append(os.path.join(directory, file))
            if topdown is False:
                paths.append(directory)
    else:
        paths.append(path)

    return paths
