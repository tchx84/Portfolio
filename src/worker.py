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


class PortfolioWorker(threading.Thread, GObject.GObject):
    __gtype_name__ = 'PortfolioWorker'

    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'updated': (GObject.SIGNAL_RUN_FIRST, None, (int, int)),
        'finished': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'failed': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        threading.Thread.__init__(self)

    def _emit_signal(self, signal, *args):
        self.emit(signal, *args)


class PortfolioCopyWorker(PortfolioWorker):
    __gtype_name__ = 'PortfolioCopyWorker'

    def __init__(self, paths, directory=None):
        super().__init__()
        self._paths = paths
        self._directory = directory

    def run(self):
        total = len(self._paths)
        GLib.idle_add(self._emit_signal, 'started', total)

        for index, path in enumerate(self._paths):
            if os.path.isdir(path):
                name = os.path.basename(path)
                destination = os.path.join(self._directory, name)
                shutil.copytree(path, destination)
            else:
                shutil.copy(path, self._directory)

            GLib.idle_add(self._emit_signal, 'updated', index, total)

        GLib.idle_add(self._emit_signal, 'finished', total)


class PortfolioCutWorker(PortfolioCopyWorker):
    __gtype_name__ = 'PortfolioCutWorker'

    def run(self):
        total = len(self._paths)
        GLib.idle_add(self._emit_signal, 'started', total)

        for index, path in enumerate(self._paths):
            name = os.path.basename(path)
            destination = os.path.join(self._directory, name)
            shutil.move(path, destination)

            GLib.idle_add(self._emit_signal, 'updated', index, total)

        GLib.idle_add(self._emit_signal, 'finished', total)


class PortfolioDeleteWorker(PortfolioCopyWorker):
    __gtype_name__ = 'PortfolioDeleteWorker'

    def run(self):
        total = len(self._paths)
        GLib.idle_add(self._emit_signal, 'started', total)

        for index, path in enumerate(self._paths):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)

            GLib.idle_add(self._emit_signal, 'updated', index, total)

        GLib.idle_add(self._emit_signal, 'finished', total)
