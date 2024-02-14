# operation.py
#
# Copyright 2024 Martin Abente Lahaye
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

from gi.repository import GObject

from .translation import gettext as _
from .worker import PortfolioDeleteWorker
from .worker import PortfolioSendTrashWorker
from .history import default_history
from .trash import default_trash


class BaseOperation(GObject.GObject):
    __gsignals__ = {
        "decision": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (str, callable, callable, callable),
        ),
        "started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str, float, str, str)),
        "finished": (GObject.SignalFlags.RUN_LAST, None, ()),
        "failed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, files, button):
        super().__init__()

        self.files = files
        self.button = button
        self.worker = None


class RenameOperation(BaseOperation):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.button.connect("clicked", self.__on_operation_triggered)

        self.files.connect("rename-started", self.__on_operation_started)
        self.files.connect("rename-finished", self.__on_operation_finished)
        self.files.connect("rename-failed", self.__on_operation_failed)

    def __on_operation_triggered(self, *args):
        self.files.rename_selected_row()

    def __on_operation_started(self, *args):
        self.emit("started")

    def __on_operation_finished(self, *args):
        self.emit("finished")

    def __on_operation_failed(self, files, name):
        self.files.rename_selected_row()
        self.emit(
            "updated",
            _("%s already exists") % name,
            None,
            None,
            None,
        )


class DeleteOperation(BaseOperation):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.selection = []
        self.button.connect("clicked", self.__on_operation_triggered)

    def __on_operation_triggered(self, button):
        self.selection = self.files.get_selection()
        count = len(self.selection)

        if count == 1:
            name = os.path.basename(self.selection[0][0])
        else:
            name = _("these %d files") % count

        self.emit(
            "decision",
            _("Delete %s permanently?") % name,
            self.__on_operation_confirmed,
            self.__on_operation_cancelled,
            self.__on_operation_alternative
            if default_trash.has_trash(default_history.directory)
            else None,
        )

    def __on_operation_confirmed(self, button, popup):
        self.worker = PortfolioDeleteWorker(self.selection)
        self.worker.connect("started", self.__on_operation_started)
        self.worker.connect("pre-update", self.__on_operation_before_updated)
        self.worker.connect("updated", self.__on_operation_updated)
        self.worker.connect("finished", self.__on_operation_finished)
        self.worker.connect("failed", self.__on_operation_failed)
        self.worker.connect("stopped", self.__on_operation_stopped)
        self.worker.start()

    def __on_operation_cancelled(self, button, popup, selection):
        self.emit("finished")

    def __on_operation_alternative(self, button, popup):
        self.worker = PortfolioSendTrashWorker(self.selection)
        self.worker.connect("started", self.__on_operation_started)
        self.worker.connect("pre-update", self.__on_operation_before_updated)
        self.worker.connect("updated", self.__on_operation_updated)
        self.worker.connect("finished", self.__on_operation_finished)
        self.worker.connect("failed", self.__on_operation_failed)
        self.worker.connect("stopped", self.__on_operation_stopped)
        self.worker.start()

    def __on_operation_started(self):
        self.emit("started")
        self.emit("updated", _("Deleting"), 0.0, "", "")

    def __on_operation_before_updated(self, worker, path):
        self.emit("updated", os.path.basename(path), None, None, None)

    def __on_operation_updated(self, worker, path, row, index, total):
        self.files.remove_row(row)
        self.emit("updated", None, (index + 1) / total, None, None)

    def __on_operation_finished(self, worker, total):
        self.fininsh()

    def __on_operation_failed(self, worker, path):
        name = os.path.basename(path)
        self.emit("updated", _("Could not delete %s") % name, None, None, None)
        self.emit("failed")

    def __on_operation_stopped(self, worker):
        self.finish()

    def finish(self):
        if self.worker is not None:
            self.worker.stop()

        self.worker = None
        self.selection = []
        self.emit("finished")
