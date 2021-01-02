# worker.py
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
import shutil
import threading

from gi.repository import GObject, GLib

from . import utils
from . import logger


class PortfolioWorker(threading.Thread, GObject.GObject):
    __gtype_name__ = "PortfolioWorker"

    def __init__(self):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class PortfolioCopyWorker(PortfolioWorker):
    __gtype_name__ = "PortfolioCopyWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, bool, bool, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, selection, directory=None):
        super().__init__()
        self._selection = selection
        self._directory = directory

    def run(self):
        paths = {}
        renames = {}

        for path, ref in self._selection:
            for _path in utils.flatten_walk(path):
                paths[_path] = path

        total = len(paths)
        self.emit("started", total)

        for index, path in enumerate(paths.keys()):
            parent = paths.get(path)
            posfix = path.replace(f"{os.path.dirname(parent)}{os.path.sep}", "")
            destination = os.path.join(self._directory, posfix)

            rename = renames.get(parent)
            if rename is not None:
                destination = destination.replace(parent, rename)

            parent = os.path.dirname(destination)
            overwritten = os.path.exists(destination)
            ignore = paths.get(path) != path

            if path == destination:
                name = os.path.basename(destination)
                name = utils.find_new_name(self._directory, name)
                destination = os.path.join(self._directory, name)
                renames[path] = destination
                overwritten = False

            try:
                if overwritten and os.path.isdir(destination):
                    shutil.rmtree(destination)
                if not os.path.exists(parent):
                    os.makedirs(parent)
                if os.path.isdir(path):
                    os.makedirs(destination)
                else:
                    shutil.copyfile(path, destination)
            except Exception as e:
                logger.debug(e)
                self.emit("failed", destination)
                return
            else:
                self.emit("updated", destination, overwritten, ignore, index, total)

        self.emit("finished", total)


class PortfolioCutWorker(PortfolioCopyWorker):
    __gtype_name__ = "PortfolioCutWorker"

    def run(self):
        paths = {}

        for path, ref in self._selection:
            for _path in utils.flatten_walk(path):
                paths[_path] = path

        total = len(paths)
        self.emit("started", total)

        last_selected_parent = None
        for index, path in enumerate(paths.keys()):

            selected_parent = paths.get(path)
            selected_subpath = path.replace(
                f"{os.path.dirname(selected_parent)}{os.path.sep}", ""
            )
            destination = os.path.join(self._directory, selected_subpath)
            overwritten = os.path.exists(destination)
            ignore = selected_parent != path

            try:
                if path == destination:
                    continue

                if overwritten and os.path.isdir(destination):
                    shutil.rmtree(destination)

                if os.path.isdir(path):
                    os.makedirs(destination)
                else:
                    shutil.move(path, destination)

                # If done with last selected directory remove it
                if (
                    last_selected_parent is not None
                    and os.path.isdir(last_selected_parent)
                    and selected_parent != last_selected_parent
                ):
                    shutil.rmtree(last_selected_parent)

                # Last chance to remove last selected directory
                if index == total - 1 and os.path.isdir(selected_parent):
                    shutil.rmtree(selected_parent)
            except Exception as e:
                logger.debug(e)
                self.emit("failed", path)
                return
            else:
                self.emit("updated", destination, overwritten, ignore, index, total)
                last_selected_parent = selected_parent

        self.emit("finished", total)


class PortfolioDeleteWorker(PortfolioWorker):
    __gtype_name__ = "PortfolioDeleteWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, selection):
        super().__init__()
        self._selection = selection

    def run(self):
        refs = {}

        for path, ref in self._selection:
            for _path in utils.flatten_walk(path, False):
                refs[_path] = None
            refs[path] = ref

        total = len(refs.keys())
        self.emit("started", total)

        for index, path in enumerate(refs.keys()):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
            except Exception as e:
                logger.debug(e)
                self.emit("failed", path)
                return
            else:
                ref = refs.get(path)
                self.emit("updated", path, ref, index, total)

        self.emit("finished", total)


class PortfolioLoadWorker(GObject.GObject):
    __gtype_name__ = "PortfolioLoadWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    BUFFER = 75

    def __init__(self, directory, hidden=False):
        super().__init__()
        self._directory = directory
        self._hidden = hidden

    def start(self):
        self.emit("started", self._directory)
        self._paths = os.listdir(self._directory)
        self._total = len(self._paths)
        self._index = 0
        GLib.idle_add(self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20)

    def step(self):
        if self._index >= self._total:
            self.emit("finished", self._directory)
            return

        found = []
        for index in range(0, self.BUFFER):
            if self._index + index < self._total:
                name = self._paths[self._index + index]
                if not self._hidden and name.startswith("."):
                    continue
                path = os.path.join(self._directory, name)
                found.append((name, path))

        self._index += self.BUFFER
        self.emit("updated", self._directory, found, self._index, self._total)
        GLib.idle_add(self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20)
