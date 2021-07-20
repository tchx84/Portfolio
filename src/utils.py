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

from gi.repository import Gio, GLib

from .cache import cached
from .translation import gettext as _


def find_new_name(directory, name, fmt="%s(%d)"):
    counter = 1

    while os.path.exists(os.path.join(directory, name)):
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


def get_trash_uri_scheme():
    return "trash"


def get_trash_display_name():
    return _("Trash")


def has_trash():
    return Gio.File.new_for_uri("trash:").query_exists(None)


def is_trash(uri):
    try:
        uri = GLib.uri_parse(uri, GLib.UriFlags.NONE)
        return uri.get_scheme() == get_trash_uri_scheme()
    except:
        return False


def is_uri(uri):
    try:
        GLib.uri_parse(uri, GLib.UriFlags.NONE)
        return True
    except:
        return False


def join_uri(uri, name):
    parsed_uri = GLib.uri_parse(uri, GLib.UriFlags.NONE)
    return GLib.uri_join(
        GLib.UriFlags.NONE,
        parsed_uri.get_scheme(),
        None,
        None,
        -1,
        os.path.join(parsed_uri.get_path(), name),
        None,
        None,
    )


def get_uri_path(string):
    try:
        uri = GLib.uri_parse(string, GLib.UriFlags.NONE)
        return uri.get_path()
    except:
        return string


def get_uri_info(uri, attributes):
    file = Gio.File.new_for_uri(uri)
    info = file.query_info(
        attributes,
        Gio.FileQueryInfoFlags.NONE,
        None,
    )

    return info


def get_uri_target_uri(uri):
    info = get_uri_info(uri, Gio.FILE_ATTRIBUTE_STANDARD_TARGET_URI)
    return info.get_attribute_as_string(Gio.FILE_ATTRIBUTE_STANDARD_TARGET_URI)


def list_uri(uri):
    uris = []

    file = Gio.File.new_for_uri(uri)
    enumerator = file.enumerate_children(
        f"{Gio.FILE_ATTRIBUTE_STANDARD_NAME}",
        Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
        None,
    )

    while True:
        info = enumerator.next_file(None)
        if info is None:
            break
        uris.append(info.get_name())

    return uris


def get_uri_file_name(uri):
    uri_obj = GLib.uri_parse(uri, GLib.UriFlags.NONE)
    name = os.path.basename(uri_obj.get_path())

    if uri_obj.get_scheme() == get_trash_uri_scheme() and not name:
        name = get_trash_display_name()

    return name


def get_uri_orig_path(uri):
    info = get_uri_info(uri, Gio.FILE_ATTRIBUTE_TRASH_ORIG_PATH)
    return info.get_attribute_as_string(Gio.FILE_ATTRIBUTE_TRASH_ORIG_PATH)


def get_uri_modified_time(uri):
    info = get_uri_info(uri, Gio.FILE_ATTRIBUTE_TIME_MODIFIED)
    time = info.get_modification_date_time()
    return time.to_unix()


def is_uri_dir(uri):
    info = get_uri_info(uri, Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
    return info.get_content_type() == "inode/directory"


@cached
def get_file_name(string):
    if is_uri(string):
        return get_uri_file_name(string)
    else:
        return os.path.basename(string)


@cached
def get_file_mtime(string):
    if is_uri(string):
        return get_uri_modified_time(string)
    else:
        return os.path.getmtime(string)


@cached
def is_file_dir(string):
    if is_uri(string):
        return is_uri_dir(string)
    else:
        return os.path.isdir(string)


def list_directory(string):
    if is_uri(string):
        return list_uri(string)
    else:
        return os.listdir(string)


def join_directory(directory, name):
    if is_uri(directory):
        return join_uri(directory, name)
    else:
        return os.path.join(directory, name)


def is_flatpak():
    return os.path.exists(os.path.join(os.path.sep, ".flatpak-info"))


def find_mount_point(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path
