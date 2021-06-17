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
import locale
import datetime
import threading
import subprocess

from gi.repository import Gio, GObject, GLib

from . import utils
from . import logger
from .translation import gettext as _


class WorkerStoppedException(Exception):
    pass


class PortfolioWorker(threading.Thread, GObject.GObject):
    __gtype_name__ = "PortfolioWorker"

    def __init__(self):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        self._cancellable = Gio.Cancellable()

    def _progress(self, current, total):
        logger.debug(current, total)

    def _copy(self, source, destination):
        source = Gio.File.new_for_path(source)
        destination = Gio.File.new_for_path(destination)

        try:
            source.copy(destination, Gio.FileCopyFlags.OVERWRITE, self._cancellable)
        except GLib.Error as e:
            if e.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                raise WorkerStoppedException()
            raise

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
        "pre-update": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, bool, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "stopped": (GObject.SignalFlags.RUN_LAST, None, ()),
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
                self._stop_check()
                self.emit("pre-update", _destination)
                self._copy(_path, _destination)
                self.emit("updated", _destination, True, count, total)
                count += 1

            try:
                self._stop_check()
                self.emit("pre-update", destination)
                if os.path.isdir(path):
                    if overwritten and os.path.isdir(path):
                        shutil.rmtree(destination)
                    shutil.copytree(path, destination, copy_function=_callback)
                else:
                    self._copy(path, destination)
            except WorkerStoppedException:
                self.emit("stopped")
                return
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
                self._stop_check()
                self.emit("pre-update", _destination)
                self._copy(_path, _destination)
                self.emit("updated", _destination, True, count, total)
                count += 1

            try:
                self._stop_check()
                self.emit("pre-update", destination)
                if destination == path:
                    continue
                if overwritten and os.path.isdir(path):
                    shutil.rmtree(destination)
                shutil.move(path, destination, copy_function=_callback)
            except WorkerStoppedException:
                self.emit("stopped")
                return
            except Exception as e:
                logger.debug(e)
                self.emit("failed", path)
                return
            else:
                self.emit("updated", destination, overwritten, count, total)
                count += 1

        self.emit("finished", total)


class PortfolioDeleteWorker(GObject.GObject):
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

    def start(self):
        self.emit("started")
        Gio.AppInfo.launch_default_for_uri_async(
            f"file://{self._path}", None, None, self._on_launch_finished, None
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
                        size += os.path.getsize(os.path.join(directory, filename))
                    except:
                        pass

            self._worker._size = self._worker._human_size(size)
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
        return os.path.getsize(self._path)

    def _update_size(self):
        if os.path.isdir(self._path):
            self._inner_worker = self.InnerWorker(self)
            self._inner_worker.start()
        else:
            self._size = self._human_size(self._get_file_size())
            self.notify("size")

    # https://gist.github.com/cbwar/d2dfbc19b140bd599daccbe0fe925597
    def _human_size(self, num):
        for unit in ["", "k", "M", "G", "T", "P", "E", "Z"]:
            if abs(num) < 1024.0:
                return "%3.1f %sB" % (num, unit)
            num /= 1024.0
        return "%.1f%sB" % (num, "Yi")

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
            Gio.FileQueryInfoFlags.NONE,
            None,
        )

        self._name = os.path.basename(self._path)
        self._location = os.path.dirname(self._path)
        self._type = info.get_content_type()
        self._size = _("Calculating...")
        self._created = self._get_human_time(os.path.getctime(self._path))
        self._modified = self._get_human_time(os.path.getmtime(self._path))
        self._accessed = self._get_human_time(os.path.getatime(self._path))

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


class PortfolioLoadTrashWorker(GObject.GObject):
    __gtype_name__ = "PortfolioLoadTrashWorker"

    __gsignals__ = {
        "started": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, object, int, int)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, uri, hidden=False):
        super().__init__()
        self._uri = uri
        self._cancellable = Gio.Cancellable()
        self._timeout_handler_id = None

    def _get_total(self):
        # XXX there HAS to be a better way
        total = 0

        file = Gio.File.new_for_uri(self._uri)
        enumerator = file.enumerate_children(
            "",
            Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
            None,
        )

        while enumerator.next_file(None) is not None:
            total += 1

        return total

    def start(self):
        self.emit("started", self._uri)

        self._trash = Gio.File.new_for_uri(self._uri)
        self._enumerator = self._trash.enumerate_children(
            f"{Gio.FILE_ATTRIBUTE_STANDARD_NAME},{Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME},{Gio.FILE_ATTRIBUTE_TRASH_ORIG_PATH}",
            Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
            self._cancellable,
        )

        self._index = 1
        self._total = self._get_total()
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def step(self):
        info = self._enumerator.next_file(self._cancellable)

        if info is None:
            self.emit("finished", self._uri)
            return

        name = info.get_display_name()

        uri = GLib.uri_parse(self._uri, GLib.UriFlags.NONE)
        uri = GLib.uri_join(
            GLib.UriFlags.NONE,
            uri.get_scheme(),
            None,
            None,
            -1,
            os.path.join(uri.get_path(), info.get_name()),
            None,
            None,
        )

        self.emit(
            "updated",
            self._uri,
            [[name, uri]],
            self._index,
            self._total,
        )
        self._timeout_handler_id = GLib.idle_add(
            self.step, priority=GLib.PRIORITY_HIGH_IDLE + 20
        )

    def stop(self):
        if not self._cancellable.is_cancelled():
            self._cancellable.cancel()
        if self._timeout_handler_id is not None:
            GLib.Source.remove(self._timeout_handler_id)
            self._timeout_handler_id = None


class PortfolioSendTrashWorker(GObject.GObject):
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

            if os.path.exists(os.path.join(os.path.sep, ".flatpak-info")):
                cmd = f'flatpak-spawn --host gio trash "{path}"'
                subprocess.run(cmd, shell=True, check=True)
            else:
                file = Gio.File.new_for_path(path)
                file.trash()
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


class PortfolioRestoreTrashWorker(GObject.GObject):
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

            file = Gio.File.new_for_uri(path)
            info = file.query_info(
                Gio.FILE_ATTRIBUTE_TRASH_ORIG_PATH,
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                None,
            )

            original_path = info.get_attribute_as_string(
                Gio.FILE_ATTRIBUTE_TRASH_ORIG_PATH
            )
            original_parent = os.path.dirname(original_path)
            original_file = Gio.File.new_for_path(original_path)

            if not os.path.exists(original_parent):
                os.makedirs(original_parent)

            file.move(original_file, Gio.FileCopyFlags.OVERWRITE, None)
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
            file = Gio.File.new_for_uri(path)
            file.delete()
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
