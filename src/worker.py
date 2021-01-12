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
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, bool, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, selection, directory=None):
        super().__init__()
        self._selection = selection
        self._directory = directory

    def run(self):
        count = 0
        total = sum([utils.count(path) for path, ref in self._selection])
        self.emit("started", total)

        for path, ref in self._selection:
            name = os.path.basename(path)
            destination = os.path.join(self._directory, name)
            overwritten = os.path.exists(destination)

            if path == destination:
                name = utils.find_new_name(self._directory, name)
                destination = os.path.join(self._directory, name)
                overwritten = False

            def _callback(_path, _destination):
                nonlocal count, total
                self.emit("pre-update", _destination)
                shutil.copy2(_path, _destination)
                self.emit("updated", _destination, True, count, total)
                count += 1

            try:
                self.emit("pre-update", destination)
                if os.path.isdir(path):
                    if overwritten and os.path.isdir(path):
                        shutil.rmtree(destination)
                    shutil.copytree(path, destination, copy_function=_callback)
                else:
                    shutil.copyfile(path, destination)
            except Exception as e:
                logger.debug(e)
                self.emit("failed", destination)
                return
            else:
                self.emit("updated", destination, overwritten, count, total)
                count += 1

        self.emit("finished", total)


class PortfolioCutWorker(PortfolioCopyWorker):
    __gtype_name__ = "PortfolioCutWorker"

    def run(self):
        count = 0
        total = sum([utils.count(path) for path, ref in self._selection])
        self.emit("started", total)

        for path, ref in self._selection:
            name = os.path.basename(path)
            destination = os.path.join(self._directory, name)
            overwritten = os.path.exists(destination)

            def _callback(_path, _destination):
                nonlocal count, total
                self.emit("pre-update", _destination)
                shutil.copy2(_path, _destination)
                self.emit("updated", _destination, True, count, total)
                count += 1

            try:
                self.emit("pre-update", destination)
                if destination == path:
                    continue
                if overwritten and os.path.isdir(path):
                    shutil.rmtree(destination)
                shutil.move(path, destination, copy_function=_callback)
            except Exception as e:
                logger.debug(e)
                self.emit("failed", path)
                return
            else:
                self.emit("updated", destination, overwritten, count, total)
                count += 1

        self.emit("finished", total)


class PortfolioDeleteWorker(PortfolioWorker):
    __gtype_name__ = "PortfolioDeleteWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, selection):
        super().__init__()
        self._selection = selection

    def run(self):
        self.emit("started")

        try:
            paths = []
            for path, ref in self._selection:
                paths += utils.flatten_walk(path)
        except Exception as e:
            logger.debug(e)
            self.emit("failed", path)
            return

        refs = dict(self._selection)
        total = len(paths)

        for index, path in enumerate(paths):
            try:
                self.emit("pre-update", path)
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
                    os.unlink(path)
            except Exception as e:
                logger.debug(e)
                self.emit("failed", path)
                return
            else:
                self.emit("updated", path, refs.get(path), index, total)

        self.emit("finished", total)


class PortfolioLoadWorker(GObject.GObject):
    __gtype_name__ = "PortfolioLoadWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    BUFFER = 75

    def __init__(self, directory, hidden=False):
        super().__init__()
        self._directory = directory
        self._hidden = hidden

    def start(self):
        self.emit("started", self._directory)

        try:
            self._paths = os.listdir(self._directory)
        except Exception as e:
            logger.debug(e)
            self.emit("failed", self._directory)
            return

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
