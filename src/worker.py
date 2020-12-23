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
import time
import shutil
import threading

from gi.repository import GObject, GLib


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
        "started": (GObject.SIGNAL_RUN_LAST, None, (int,)),
        "updated": (GObject.SIGNAL_RUN_LAST, None, (int, int)),
        "finished": (GObject.SIGNAL_RUN_LAST, None, (int,)),
        "failed": (GObject.SIGNAL_RUN_LAST, None, (str,)),
    }

    def __init__(self, paths, directory=None):
        super().__init__()
        self._paths = paths
        self._directory = directory

    def run(self):
        total = len(self._paths)
        self.emit("started", total)

        for index, path in enumerate(self._paths):
            try:
                if os.path.isdir(path):
                    name = os.path.basename(path)
                    destination = os.path.join(self._directory, name)
                    shutil.copytree(path, destination)
                else:
                    shutil.copy(path, self._directory)
            except:
                self.emit("failed", path)
                return
            else:
                self.emit("updated", index, total)

        self.emit("finished", total)


class PortfolioCutWorker(PortfolioCopyWorker):
    __gtype_name__ = "PortfolioCutWorker"

    def run(self):
        total = len(self._paths)
        self.emit("started", total)

        for index, path in enumerate(self._paths):
            try:
                name = os.path.basename(path)
                destination = os.path.join(self._directory, name)
                shutil.move(path, destination)
            except:
                self.emit("failed", path)
                return
            else:
                self.emit("updated", index, total)

        self.emit("finished", total)


class PortfolioDeleteWorker(PortfolioCopyWorker):
    __gtype_name__ = "PortfolioDeleteWorker"

    def run(self):
        total = len(self._paths)
        self.emit("started", total)

        for index, path in enumerate(self._paths):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
            except:
                self.emit("failed", path)
                return
            else:
                self.emit("updated", index, total)

        self.emit("finished", total)


class PortfolioLoadWorker(PortfolioWorker):
    __gtype_name__ = "PortfolioLoadWorker"

    __gsignals__ = {
        "started": (GObject.SIGNAL_RUN_LAST, None, (str,)),
        "updated": (GObject.SIGNAL_RUN_LAST, None, (str, str, str, int, int)),
        "finished": (GObject.SIGNAL_RUN_LAST, None, (str,)),
        "failed": (GObject.SIGNAL_RUN_LAST, None, (str,)),
    }

    def __init__(self, directory):
        super().__init__()
        self._directory = directory

    def run(self):
        self.emit("started", self._directory)

        paths = os.listdir(self._directory)
        total = len(paths)
        found = []

        for index, name in enumerate(paths):
            try:
                if name.startswith("."):
                    continue
                path = os.path.join(self._directory, name)
                found.append([path, name])
            except:
                self.emit("failed", self._directory)
                return
            else:
                self.emit("updated", self._directory, path, name, index, total)
                time.sleep(0.001)

        self.emit("finished", self._directory)
