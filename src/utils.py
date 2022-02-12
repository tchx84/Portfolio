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

from gi.repository import GLib

from .cache import cached


def find_new_name(directory, name, fmt="%s(%d)"):
    counter = 1

    while os.path.lexists(os.path.join(directory, name)):
        components = re.split("(\(\d+\)$)", name)
        if len(components) > 1:
            name = "".join(components[:-2])

        name = fmt % (name, counter)
        counter += 1

    return name


def count(path):
    _count = 1

    if os.path.isdir(path):
        for directory, dirs, files in os.walk(path):
            _count += len(files)

    return _count


def flatten_walk(path):
    _paths = []

    def _callback(error):
        raise error

    if os.path.isdir(path):
        for directory, dirs, files in os.walk(path, topdown=False, onerror=_callback):
            for file in files:
                _paths += [os.path.join(directory, file)]
            _paths += [directory]
    else:
        _paths += [path]

    return _paths


def get_uri_path(string):
    try:
        uri = GLib.uri_parse(string, GLib.UriFlags.NONE)
        return uri.get_path()
    except:
        return string


@cached
def get_file_mtime(string):
    return os.lstat(string).st_mtime


@cached
def is_file_dir(string):
    return os.path.isdir(string)


def is_flatpak():
    return os.path.exists(os.path.join(os.path.sep, ".flatpak-info"))


def sync_folder(path):
    fd = os.open(path, os.O_DIRECTORY)
    os.fsync(fd)
    os.close(fd)


def find_mount_point(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


# https://gist.github.com/cbwar/d2dfbc19b140bd599daccbe0fe925597
def get_size_for_humans(num):
    for unit in ["", "k", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1000.0:
            return "%3.1f %sB" % (num, unit)
        num /= 1000.0
    return "%.1f%sB" % (num, "Y")
