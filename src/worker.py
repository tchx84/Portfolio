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
import sys
import time
import shutil
import locale
import datetime
import threading

from gi.repository import Gio, GObject, GLib

from . import utils
from . import logger
from .cache import default_cache
from .translation import gettext as _
from .trash import default_trash


class WorkerStoppedException(Exception):
    pass


class CachedWorker(object):
    def __init__(self):
        default_cache.activate()

    def __del__(self):
        default_cache.deactivate()


class PortfolioWorker(threading.Thread, GObject.GObject):
    __gtype_name__ = "PortfolioWorker"

    def __init__(self):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        self._cancellable = Gio.Cancellable()

    def _progress(self, current, total):
        logger.debug(current, total)

    def _stop_check(self):
        if self._cancellable.is_cancelled():
            raise WorkerStoppedException()

    def stop(self):
        if not self._cancellable.is_cancelled():
            self._cancellable.cancel()

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class PortfolioCopyWorker(PortfolioWorker):
    __gtype_name__ = "PortfolioCopyWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str, bool)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, int, int, float, float)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "stopped": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, selection, directory=None):
        super().__init__()
        self._selection = selection
        self._directory = directory

    def _do_copy(self, source, destination, callback):
        current_bytes = 0
        total_bytes = os.stat(source.name).st_size
        arch_capped = sys.maxsize < 2**32

        # start with an arbitrary block size
        block_min_bytes = 2**23
        block_bytes = block_min_bytes
        last_sync = time.monotonic()

        outfd = destination.fileno()
        infd = source.fileno()

        while True:
            self._stop_check()

            # assume kernel >= 2.6.33
            sent_bytes = os.sendfile(outfd, infd, current_bytes, block_bytes)
            if sent_bytes == 0:
                break

            # fsync frequency is indirectly controlled by the size of the block
            os.fsync(outfd)

            # now dynamically adjust the block size so that it
            # will keep fsync frequency between 750 and 1250ms
            now = time.monotonic()
            if now - last_sync > 1.25:
                block_bytes //= 2
            elif now - last_sync < 0.75:
                block_bytes *= 2

            # on 32 bit arch block size must be capped
            if arch_capped:
                block_bytes = min(block_bytes, 2**30)

            # some lower and upper bounds
            block_bytes = max(block_bytes, block_min_bytes)
            block_bytes = min(block_bytes, total_bytes)

            last_sync = now
            current_bytes += sent_bytes
            callback(current_bytes, total_bytes)

        logger.debug(f"sendfile block size converged to {block_bytes}")

    def _copy(self, source_path, destination_path):
        if os.path.islink(source_path):
            os.symlink(os.readlink(source_path), destination_path)
            return

        def callback(current_bytes, total_bytes):
            self.emit(
                "updated",
                destination_path,
                self._count,
                self._total,
                current_bytes,
                total_bytes,
            )

        with open(source_path, "rb") as source:
            with open(destination_path, "wb") as destination:
                self._do_copy(source, destination, callback)

        shutil.copymode(source_path, destination_path)

        self._count += 1

    def run(self):
        self._count = 0
        self._total = sum([utils.count(path) for path, ref in self._selection])

        self.emit("started", self._total)

        for path, ref in self._selection:
            name = os.path.basename(path)
            destination = os.path.join(self._directory, name)
            overwritten = os.path.lexists(destination)

            if path == destination:
                name = utils.find_new_name(self._directory, name)
                destination = os.path.join(self._directory, name)
                overwritten = False

            try:
                self._stop_check()
                self.emit("pre-update", destination, overwritten)

                if os.path.isdir(path):
                    if overwritten and os.path.isdir(path):
                        shutil.rmtree(destination)
                    shutil.copytree(path, destination, copy_function=self._copy)
                else:
                    self._copy(path, destination)
            except WorkerStoppedException:
                self.emit("stopped")
                return
            except Exception as e:
                logger.debug(e)
                self.emit("failed", destination)
                return
            finally:
                utils.sync_folder(os.path.dirname(destination))

        self.emit("finished", self._total)


class PortfolioCutWorker(PortfolioCopyWorker):
    __gtype_name__ = "PortfolioCutWorker"

    def run(self):
        self._count = 0
        self._total = sum([utils.count(path) for path, ref in self._selection])

        self.emit("started", self._total)

        for path, ref in self._selection:
            name = os.path.basename(path)
            destination = os.path.join(self._directory, name)
            overwritten = os.path.lexists(destination)

            try:
                self._stop_check()
                self.emit("pre-update", destination, overwritten)

                if destination == path:
                    continue
                if overwritten and os.path.isdir(path):
                    shutil.rmtree(destination)
                if overwritten and os.path.islink(destination):
                    os.unlink(destination)
                shutil.move(path, destination, copy_function=self._copy)
            except WorkerStoppedException:
                self.emit("stopped")
                return
            except Exception as e:
                logger.debug(e)
                self.emit("failed", path)
                return
            finally:
                utils.sync_folder(os.path.dirname(destination))

        self.emit("finished", self._total)


class PortfolioDeleteWorker(GObject.GObject, CachedWorker):
    __gtype_name__ = "PortfolioDeleteWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "stopped": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, selection):
        super().__init__()
        CachedWorker.__init__(self)
        self._selection = selection
        self._timeout_handler_id = None

    def start(self):
        self.emit("started")

        try:
            paths = []
            for path, ref in self._selection:
                paths += utils.flatten_walk(path)
        except Exception as e:
            logger.debug(e)
            self.emit("failed", path)
            return

        self._paths = paths
        self._refs = dict(self._selection)

        self._total = len(paths)
        self._index = 0
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def step(self):
        if self._index >= self._total:
            self.emit("finished", self._total)
            return

        path = self._paths[self._index]

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

        self._index += 1
        self.emit("updated", path, self._refs.get(path), self._index, self._total)
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def stop(self):
        if self._timeout_handler_id is not None:
            GLib.Source.remove(self._timeout_handler_id)
            self._timeout_handler_id = None
        self.emit("stopped")


class PortfolioLoadWorker(GObject.GObject, CachedWorker):
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
        CachedWorker.__init__(self)
        self._directory = directory
        self._hidden = hidden
        self._timeout_handler_id = None

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
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

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
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def stop(self):
        if self._timeout_handler_id is None:
            return
        GLib.Source.remove(self._timeout_handler_id)
        self._timeout_handler_id = None


class PortfolioOpenWorker(GObject.GObject):
    __gtype_name__ = "PortfolioOpenWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "updated": (GObject.SignalFlags.RUN_LAST, None, ()),
        "finished": (GObject.SignalFlags.RUN_LAST, None, ()),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, path):
        super().__init__()
        self._path = path
        self._timeout_handler_id = None
        self._is_flatpak = utils.is_flatpak()

    def start(self):
        self.emit("started")

        uri = f"file://{self._path}"
        Gio.AppInfo.launch_default_for_uri_async(
            uri, None, None, self._on_launch_finished, None
        )
        self._timeout_handler_id = GLib.timeout_add(100, self._on_step)

    def stop(self):
        pass

    def _on_step(self):
        self.emit("updated")
        return True

    def _on_launch_finished(self, worker, result, data=None):
        if self._timeout_handler_id is not None:
            GLib.Source.remove(self._timeout_handler_id)
            self._timeout_handler_id = None

        if result.had_error():
            self.emit("failed", self._path)
        else:
            self.emit("finished")


class PortfolioPropertiesWorker(GObject.GObject):
    class InnerWorker(threading.Thread):
        def __init__(self, worker):
            super().__init__()
            self._stop = False
            self._worker = worker

        def stop(self):
            self._stop = True

        def run(self):
            size = 0

            for directory, folders, files in os.walk(self._worker._path):
                for filename in files:
                    if self._stop:
                        return
                    try:
                        size += os.lstat(os.path.join(directory, filename)).st_size
                    except:
                        pass

            self._worker._size = utils.get_size_for_humans(size)
            GLib.idle_add(self._worker.notify, "size")

    def __init__(self):
        super().__init__()

        self._path = ""
        self._name = ""
        self._location = ""
        self._type = ""
        self._size = ""
        self._created = ""
        self._modified = ""
        self._accessed = ""

        self._inner_worker = self.InnerWorker(self)

    def _get_file_size(self):
        return os.lstat(self._path).st_size

    def _update_size(self):
        if os.path.isdir(self._path):
            self._inner_worker = self.InnerWorker(self)
            self._inner_worker.start()
        else:
            self._size = utils.get_size_for_humans(self._get_file_size())
            self.notify("size")

    def _get_human_time(self, timestamp):
        fmt = locale.nl_langinfo(locale.D_T_FMT)
        return datetime.datetime.fromtimestamp(timestamp).strftime(fmt)

    @GObject.Property(type=str)
    def name(self):
        return self._name

    @GObject.Property(type=str)
    def location(self):
        return self._location

    @GObject.Property(type=str)
    def type(self):
        return self._type

    @GObject.Property(type=str)
    def size(self):
        return self._size

    @GObject.Property(type=str)
    def created(self):
        return self._created

    @GObject.Property(type=str)
    def modified(self):
        return self._modified

    @GObject.Property(type=str)
    def accessed(self):
        return self._accessed

    @GObject.Property(type=str)
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path

        self._inner_worker.stop()

        file = Gio.File.new_for_path(path)
        info = file.query_info(
            Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE,
            Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
            None,
        )

        self._name = os.path.basename(self._path)
        self._location = os.path.dirname(self._path)
        self._type = info.get_content_type()
        self._size = _("Calculating...")
        self._created = self._get_human_time(os.lstat(self._path).st_ctime)
        self._modified = self._get_human_time(os.lstat(self._path).st_mtime)
        self._accessed = self._get_human_time(os.lstat(self._path).st_atime)

        self.notify("name")
        self.notify("location")
        self.notify("type")
        self.notify("size")
        self.notify("created")
        self.notify("modified")
        self.notify("accessed")

        self._update_size()

    def stop(self):
        self._inner_worker.stop()


class PortfolioSendTrashWorker(GObject.GObject, CachedWorker):
    __gtype_name__ = "PortfolioSendTrashWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "stopped": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, selection):
        super().__init__()
        CachedWorker.__init__(self)
        self._selection = selection
        self._is_flatpak = utils.is_flatpak()

    def start(self):
        self.emit("started")

        self._paths = [path for path, ref in self._selection]
        self._refs = dict(self._selection)

        self._total = len(self._paths)
        self._index = 0
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def step(self):
        if self._index >= self._total:
            self.emit("finished", self._total)
            return

        path = self._paths[self._index]

        try:
            self.emit("pre-update", path)
            default_trash.trash(path)
        except Exception as e:
            logger.debug(e)
            self.emit("failed", path)
            return

        self._index += 1
        self.emit("updated", path, self._refs.get(path), self._index, self._total)
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def stop(self):
        if self._timeout_handler_id is not None:
            GLib.Source.remove(self._timeout_handler_id)
            self._timeout_handler_id = None
        self.emit("stopped")


class PortfolioRestoreTrashWorker(GObject.GObject, CachedWorker):
    __gtype_name__ = "PortfolioRestoreTrashWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "stopped": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, selection):
        super().__init__()
        CachedWorker.__init__(self)
        self._selection = selection

    def start(self):
        self.emit("started")

        self._paths = [path for path, ref in self._selection]
        self._refs = dict(self._selection)

        self._total = len(self._paths)
        self._index = 0
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def step(self):
        if self._index >= self._total:
            self.emit("finished", self._total)
            return

        path = self._paths[self._index]

        try:
            self.emit("pre-update", path)
            default_trash.restore(path)
        except Exception as e:
            logger.debug(e)
            self.emit("failed", path)
            return

        self._index += 1
        self.emit("updated", path, self._refs.get(path), self._index, self._total)
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def stop(self):
        if self._timeout_handler_id is not None:
            GLib.Source.remove(self._timeout_handler_id)
            self._timeout_handler_id = None
        self.emit("stopped")


class PortfolioDeleteTrashWorker(GObject.GObject):
    __gtype_name__ = "PortfolioDeleteTrashWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "stopped": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, selection):
        super().__init__()
        self._selection = selection

    def start(self):
        self.emit("started")

        self._paths = [path for path, ref in self._selection]
        self._refs = dict(self._selection)

        self._total = len(self._paths)
        self._index = 0
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def step(self):
        if self._index >= self._total:
            self.emit("finished", self._total)
            return

        path = self._paths[self._index]

        try:
            self.emit("pre-update", path)
            default_trash.remove(path)
        except Exception as e:
            logger.debug(e)
            self.emit("failed", path)
            return

        self._index += 1
        self.emit("updated", path, self._refs.get(path), self._index, self._total)
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def stop(self):
        if self._timeout_handler_id is not None:
            GLib.Source.remove(self._timeout_handler_id)
            self._timeout_handler_id = None
        self.emit("stopped")


class PortfolioLoadTrashWorker(GObject.GObject, CachedWorker):
    __gtype_name__ = "PortfolioLoadTrashWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, directory=None, hidden=False):
        super().__init__()
        CachedWorker.__init__(self)
        self._timeout_handler_id = None

    def start(self):
        self.emit("started", "")

        try:
            self._paths = default_trash.list()
        except Exception as e:
            logger.debug(e)
            self.emit("failed", "")
            return

        self._total = len(self._paths)
        self._index = 0
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def step(self):
        if self._index >= self._total:
            self.emit("finished", "")
            return

        path = self._paths[self._index]
        name = os.path.basename(path)

        self._index += 1
        self.emit("updated", "", [(name, path)], self._index, self._total)
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def stop(self):
        if self._timeout_handler_id is None:
            return
        GLib.Source.remove(self._timeout_handler_id)
        self._timeout_handler_id = None
