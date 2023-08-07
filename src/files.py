# files.py
#
# Copyright 2023 Martin Abente Lahaye
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

from gi.repository import Gtk, GObject

from . import utils
from .settings import PortfolioSettings


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/files.ui")
class PortfolioFiles(Gtk.TreeView):
    __gtype_name__ = "PortfolioFiles"

    __gsignals__ = {
        "selection-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "path-activated": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "path-detailed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "edit-started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "edit-finished": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    name_column = Gtk.Template.Child()
    name_cell = Gtk.Template.Child()
    sorted = Gtk.Template.Child()
    filtered = Gtk.Template.Child()
    selection = Gtk.Template.Child()
    liststore = Gtk.Template.Child()

    ICON_COLUMN = 0
    NAME_COLUMN = 1
    PATH_COLUMN = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()

    def _setup(self):
        self._editing = False
        self._to_select = None
        self._to_select_row = None
        self._last_clicked = None
        self._dont_activate = False
        self._force_select = False
        self._filter = ""
        self._sort_order = PortfolioSettings.ALPHABETICAL_ORDER

        self.filtered.set_visible_func(self._filter_func, data=None)
        self.sorted.set_default_sort_func(self._sort, None)
        self.selection.connect("changed", self._on_selection_changed)
        self.selection.set_select_function(self._on_select)
        self.connect("row-activated", self._on_row_activated)
        self.connect("button-press-event", self._on_clicked)

        self.name_cell.connect("editing-started", self._on_rename_started)
        self.name_cell.connect("edited", self._on_rename_updated)
        self.name_cell.connect("editing-canceled", self._on_rename_finished)

        self.gesture = Gtk.GestureLongPress.new(self)
        self.gesture.connect("pressed", self._on_long_pressed)

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, value):
        self._filter = value

    @property
    def to_select_row(self):
        return self._to_select_row

    @to_select_row.setter
    def to_select_row(self, value):
        self._to_select_row = value

    @property
    def sort_order(self):
        return self._sort_order

    @sort_order.setter
    def sort_order(self, value):
        self._sort_order = value

    @property
    def editing(self):
        return self._editing

    def _filter_func(self, model, row, data=None):
        path = model[row][self.PATH_COLUMN]
        if not self._filter:
            return True
        return self._filter.lower() in os.path.basename(path).lower()

    def _sort_by_last_modified(self, path1, path2):
        st_mtime1 = utils.get_file_mtime(path1)
        st_mtime2 = utils.get_file_mtime(path2)

        if st_mtime1 < st_mtime2:
            return 1
        elif st_mtime1 > st_mtime2:
            return -1

        return 0

    def _sort_by_a_to_z(self, path1, path2):
        path1 = path1.lower()
        path2 = path2.lower()

        if path1 < path2:
            return -1
        elif path1 > path2:
            return 1

        return 0

    def _sort(self, model, row1, row2, data=None):
        path1 = model[row1][self.PATH_COLUMN]
        path2 = model[row2][self.PATH_COLUMN]

        row1_is_dir = utils.is_file_dir(path1)
        row2_is_dir = utils.is_file_dir(path2)

        if row1_is_dir and not row2_is_dir:
            return -1
        elif not row1_is_dir and row2_is_dir:
            return 1

        if self._sort_order == PortfolioSettings.ALPHABETICAL_ORDER:
            return self._sort_by_a_to_z(path1, path2)
        else:
            return self._sort_by_last_modified(path1, path2)

    def _get_path(self, model, treepath):
        return model[model.get_iter(treepath)][self.PATH_COLUMN]

    def get_selection(self):
        model, treepaths = self.selection.get_selected_rows()
        selection = [
            (
                model[treepath][self.PATH_COLUMN],
                Gtk.TreeRowReference.new(model, treepath),
            )
            for treepath in treepaths
        ]
        return selection

    def _on_selection_changed(self, selection):
        self.emit("selection-changed")

    def _on_select(self, selection, model, treepath, selected, data=None):
        should_select = False

        if self._force_select is True:
            should_select = True
        elif treepath != self._last_clicked and selected:
            should_select = False
        elif treepath != self._last_clicked and not selected:
            should_select = False
        elif treepath == self._last_clicked and not selected:
            should_select = True
        elif treepath == self._last_clicked and selected:
            should_select = True

        if treepath == self._last_clicked:
            self._last_clicked = None
            self._dont_activate = True

        return should_select

    def select_all(self):
        self._force_select = True
        self.selection.select_all()
        self._force_select = False

    def unselect_all(self):
        self._force_select = True
        self.selection.unselect_all()
        self._force_select = False

    def select_row(self, row):
        self._force_select = True
        self.selection.select_iter(row)
        self._force_select = False

    def _go_to_selection(self):
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        self.set_cursor_on_cell(
            treepath, self.name_column, self.name_cell, False
        )
        self.scroll_to_cell(treepath, None, False, 0, 0)

    def go_to(self, row):
        result, row = self.filtered.convert_child_iter_to_iter(row)
        result, row = self.sorted.convert_child_iter_to_iter(row)

        treepath = self.sorted.get_path(row)

        self.scroll_to_cell(treepath, None, False, 0, 0)

    def select_and_go(self, row, edit=False):
        result, row = self.filtered.convert_child_iter_to_iter(row)
        result, row = self.sorted.convert_child_iter_to_iter(row)

        self.select_row(row)
        GLib.idle_add(self._go_to_selection)

        if edit is True:
            GLib.timeout_add(100, self._wait_and_edit)

    def go_to_top(self, *args):
        if len(self.sorted) >= 1:
            self.scroll_to_cell(0, None, True, 0, 0)

    def _on_row_activated(self, treeview, treepath, treecolumn, data=None):
        if self._dont_activate is True:
            self._dont_activate = False
            return
        if self.selection.get_mode() == Gtk.SelectionMode.NONE:
            path = self._get_path(self.sorted, treepath)
            self.emit("path-activated", path)

    def _on_clicked(self, treeview, event):
        result = self.get_path_at_pos(event.x, event.y)
        if result is None:
            return
        treepath, column, x, y = result
        self._last_clicked = treepath

    def _on_rename_started(self, cell_name, treepath, data=None):
        self._editing = True
        self.emit("edit-started")

    def _on_rename_updated(self, cell_name, treepath, new_name, data=None):
        old_path = self._get_path(self.sorted, treepath)
        directory = os.basedir(old_path)
        new_path = os.path.join(directory, new_name)

        if new_path == old_path:
            self._on_rename_finished()
            return

        try:
            # respect empty folders
            if os.path.lexists(new_path):
                raise FileExistsError(_("%s already exists") % new_path)

            os.rename(old_path, new_path)

            _treepath = Gtk.TreePath.new_from_string(treepath)
            _treepath = self.sorted.convert_path_to_child_path(_treepath)
            _treepath = self.filtered.convert_path_to_child_path(_treepath)

            row = self.liststore.get_iter(_treepath)
            self.liststore.set_value(row, self.PATH_COLUMN, new_path)
            self.liststore.set_value(row, self.NAME_COLUMN, new_name)
        except Exception as e:
            logger.debug(e)
            self._notify(
                _("%s already exists") % new_name,
                None,
                self._on_popup_closed,
                None,
                True,
                None,
            )
            self.on_rename_clicked(None)
            return

        # take the user to the new position
        self._on_rename_finished()
        self._go_to_selection()

    def _on_rename_finished(self, *args):
        self.name_cell.props.editable = False
        self._editing = False
        self.emit("edit-finished")

    def on_rename_clicked(self, button):
        self.name_cell.props.editable = True
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        self.set_cursor_on_cell(
            treepath, self.name_column, self.name_cell, True
        )

    def remove_row(self, ref):
        if ref is None or not ref.valid():
            return

        treepath = ref.get_path()
        treepath = self.sorted.convert_path_to_child_path(treepath)
        treepath = self.filtered.convert_path_to_child_path(treepath)

        self.liststore.remove(self.liststore.get_iter(treepath))

    def update_mode(self):
        count = self.selection.count_selected_rows()
        if count == 0:
            self.switch_to_navigation_mode()

    def switch_to_navigation_mode(self):
        self.selection.set_mode(Gtk.SelectionMode.NONE)

    def switch_to_selection_mode(self):
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)

    def _on_long_pressed(self, gesture, x, y):
        if self.selection.get_mode() == Gtk.SelectionMode.MULTIPLE:
            return

        self.switch_to_selection_mode()
        path = self.get_path_at_pos(x, y)

        if path is None:
            self.switch_to_navigation_mode()
            return

        treepath = path[0]
        self.selection.select_path(treepath)

        # because of the custom selection rules, is not guaranteed
        # that this will actually be selected so always update mode.
        self.update_mode()

    def _on_detail_clicked(self, button):
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        path = model[treepath][self.PATH_COLUMN]
        self.emit("path-detailed", path)

    def _on_new_folder(self, directory):
        folder_name = utils.find_new_name(directory, _("New Folder"))
        path = os.path.join(directory, folder_name)

        try:
            Path(path).mkdir(parents=False, exist_ok=True)
        except Exception as e:
            logger.debug(e)
            self._notify(
                _("No permissions on this directory"),
                None,
                self._on_popup_closed,
                None,
                True,
                None,
            )
            return

        self.switch_to_selection_mode()

        icon = utils.get_file_icon(path)
        row = self.liststore.append([icon, folder_name, path])
        self.select_and_go(row, edit=True)

    def _update_treeview(self):
        sensitive = not self._busy
        self.props.sensitive = sensitive

    def selected_count(self):
        return self.selection.count_selected_rows()

    def empty(self):
        return len(self.sorted) == 0

    def add(self, icon, name, path):
        row = self.liststore.append([icon, name, path])

        if self._to_select == path:
            self._to_select_row = row

        return row

    def clear(self):
        self.liststore.clear()