# trash.py
#
# Copyright 2021 Martin Abente Lahaye
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
import shutil

from datetime import datetime
from configparser import ConfigParser

from gi.repository import GLib, Gio, GObject

from . import utils


class PortfolioTrash(GObject.GObject):
    # https://specifications.freedesktop.org/trash-spec/trashspec-1.0.html

    __gtype_name__ = "PortfolioTrash"

    def __init__(self):
        super().__init__()

        self._manager = Gio.VolumeMonitor.get()
        self._manager.connect("mount-added", self._on_mount_changed)
        self._manager.connect("mount-removed", self._on_mount_changed)

        self.setup()

    def _setup_trash_dir(self, trash_dir):
        os.makedirs(os.path.join(trash_dir, "info"), exist_ok=True)
        os.makedirs(os.path.join(trash_dir, "files"), exist_ok=True)

    def _on_mount_changed(self, monitor, mount):
        self.setup()

    def setup(self):
        self._trash = {}

        mounts = self.get_devices_trash() + [self.get_home_trash()]
        for mount_point, trash_dir in mounts:
            self._trash[mount_point] = trash_dir

    def is_trash(self, path):
        return path == "Trash"

    def in_trash(self, path):
        if self.is_trash(path):
            return True

        for _, trash_dir in self._trash.items():
            if path.startswith(trash_dir):
                return True

        return False

    def get_home_trash(self):
        if "PORTFOLIO_XDG_DATA_DIRS" in os.environ:
            data_dir = os.environ.get("PORTFOLIO_XDG_DATA_DIRS")
        elif utils.is_flatpak() and "HOST_XDG_DATA_DIRS" in os.environ:
            data_dir = os.environ.get("HOST_XDG_DATA_DIRS")
        elif not utils.is_flatpak() and GLib.get_user_data_dir():
            data_dir = GLib.get_user_data_dir()
        else:
            data_dir = os.path.join(os.path.expanduser("~"), ".local", "share")

        self._home_trash = os.path.join(data_dir, "Trash")
        mount_point = utils.find_mount_point(data_dir)

        return mount_point, self._home_trash

    def get_devices_trash(self):
        trash = []

        for mount in self._manager.get_mounts():
            mount_point = mount.get_root().get_path()
            if not mount_point or not os.access(mount_point, os.W_OK):
                continue

            user_id = os.getuid()
            if not user_id:
                continue

            path = os.path.join(mount_point, f".Trash-{user_id}")
            trash.append((mount_point, path))

        return trash

    def get_info_path(self, path):
        files_dir = os.path.dirname(path)
        trash_dir = os.path.dirname(files_dir)
        info_dir = os.path.join(trash_dir, "info")

        info_path = os.path.join(info_dir, f"{os.path.basename(path)}.trashinfo")
        return info_path

    def get_orig_path(self, path):
        mount_point = utils.find_mount_point(path)
        trash_dir = self._trash.get(mount_point)

        info_path = self.get_info_path(path)
        info_file = ConfigParser()
        info_file.optionxform = str
        info_file.read(info_path)

        orig_path = info_file["Trash Info"]["Path"]

        # restore absolute path
        if trash_dir != self._home_trash and not os.path.isabs(orig_path):
            orig_path = os.path.join(mount_point, orig_path)

        return orig_path

    def list(self):
        paths = []

        for name, trash_dir in self._trash.items():
            files_dir = os.path.join(trash_dir, "files")
            if not os.path.exists(files_dir):
                continue
            for filename in os.listdir(files_dir):
                path = os.path.join(files_dir, filename)
                paths.append(path)

        return paths

    def trash(self, path):
        # prevent shutil.move strange behavior
        if not os.access(path, os.W_OK):
            raise PermissionError(f"Can't access {path}")

        mount_point = utils.find_mount_point(path)

        trash_dir = self._trash.get(mount_point)
        self._setup_trash_dir(trash_dir)

        files_dir = os.path.join(trash_dir, "files")
        info_dir = os.path.join(trash_dir, "info")

        name = utils.find_new_name(files_dir, os.path.basename(path), fmt="%s.%d")
        dest_path = os.path.join(files_dir, name)
        info_path = os.path.join(info_dir, f"{name}.trashinfo")

        if trash_dir == self._home_trash:
            orig_path = path
        else:
            orig_path = os.path.relpath(path, mount_point)

        info_file = ConfigParser()
        info_file.optionxform = str
        info_file["Trash Info"] = {}
        info_file["Trash Info"]["Path"] = orig_path
        info_file["Trash Info"]["DeletionDate"] = (
            datetime.utcnow().replace(microsecond=0).isoformat()
        )

        with open(info_path, "w") as info:
            info_file.write(info)
        shutil.move(path, dest_path)

    def restore(self, path):
        orig_path = self.get_orig_path(path)
        info_path = self.get_info_path(path)

        os.remove(info_path)
        shutil.move(path, orig_path)

    def remove(self, path):
        info_path = self.get_info_path(path)
        os.remove(info_path)

        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


default_trash = PortfolioTrash()
