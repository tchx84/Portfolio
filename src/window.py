# window.py
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

from pathlib import Path
from locale import gettext as _

from gi.repository import Gtk, GLib, Gio, Handy

from . import utils
from . import logger
from .popup import PortfolioPopup
from .worker import PortfolioCutWorker
from .worker import PortfolioCopyWorker
from .worker import PortfolioDeleteWorker
from .worker import PortfolioLoadWorker
from .places import PortfolioPlaces


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/window.ui")
class PortfolioWindow(Handy.ApplicationWindow):
    __gtype_name__ = "PortfolioWindow"

    name_column = Gtk.Template.Child()
    name_cell = Gtk.Template.Child()
    sorted = Gtk.Template.Child()
    filtered = Gtk.Template.Child()
    selection = Gtk.Template.Child()
    liststore = Gtk.Template.Child()
    treeview = Gtk.Template.Child()
    previous = Gtk.Template.Child()
    next = Gtk.Template.Child()
    search = Gtk.Template.Child()
    back = Gtk.Template.Child()
    rename = Gtk.Template.Child()
    delete = Gtk.Template.Child()
    cut = Gtk.Template.Child()
    copy = Gtk.Template.Child()
    paste = Gtk.Template.Child()
    select_all = Gtk.Template.Child()
    select_none = Gtk.Template.Child()
    new_folder = Gtk.Template.Child()
    loading_label = Gtk.Template.Child()
    loading_bar = Gtk.Template.Child()
    loading_description = Gtk.Template.Child()
    close_button = Gtk.Template.Child()
    help_button = Gtk.Template.Child()
    about_button = Gtk.Template.Child()
    show_hidden_button = Gtk.Template.Child()
    a_to_z_button = Gtk.Template.Child()
    go_top_button = Gtk.Template.Child()

    search_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    popup_box = Gtk.Template.Child()
    action_stack = Gtk.Template.Child()
    tools_stack = Gtk.Template.Child()
    navigation_box = Gtk.Template.Child()
    selection_box = Gtk.Template.Child()
    selection_tools = Gtk.Template.Child()
    navigation_tools = Gtk.Template.Child()
    places_box = Gtk.Template.Child()
    content_stack = Gtk.Template.Child()
    loading_box = Gtk.Template.Child()
    content_box = Gtk.Template.Child()
    app_box = Gtk.Template.Child()
    about_box = Gtk.Template.Child()
    close_box = Gtk.Template.Child()
    close_tools = Gtk.Template.Child()
    deck = Gtk.Template.Child()
    headerbar = Gtk.Template.Child()
    placeholder_box = Gtk.Template.Child()
    menu_box = Gtk.Template.Child()
    content_scroll = Gtk.Template.Child()
    go_top_revealer = Gtk.Template.Child()

    ICON_COLUMN = 0
    NAME_COLUMN = 1
    PATH_COLUMN = 2
    SEARCH_DELAY = 500

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()

    def _setup(self):
        Handy.init()

        self._popup = None
        self._worker = None
        self._busy = False
        self._editing = False
        self._to_copy = []
        self._to_cut = []
        self._last_clicked = None
        self._dont_activate = False
        self._force_select = False
        self._history = []
        self._index = -1
        self._search_delay_handler_id = 0

        self.gesture = Gtk.GestureLongPress.new(self.treeview)
        self.gesture.connect("pressed", self._on_long_pressed)

        self.filtered.set_visible_func(self._filter, data=None)
        self.sorted.set_default_sort_func(self._sort, None)
        self.selection.connect("changed", self._on_selection_changed)
        self.selection.set_select_function(self._on_select)
        self.treeview.connect("row-activated", self._on_row_activated)
        self.treeview.connect("button-press-event", self._on_clicked)

        self.name_cell.connect("editing-started", self._on_rename_started)
        self.name_cell.connect("editing-canceled", self._on_rename_finished)
        self.name_cell.connect("edited", self._on_rename_updated)

        self.previous.connect("clicked", self._on_go_previous)
        self.next.connect("clicked", self._on_go_next)
        self.rename.connect("clicked", self._on_rename_clicked)
        self.delete.connect("clicked", self._on_delete_clicked)
        self.cut.connect("clicked", self._on_cut_clicked)
        self.copy.connect("clicked", self._on_copy_clicked)
        self.paste.connect("clicked", self._on_paste_clicked)
        self.select_all.connect("clicked", self._on_select_all)
        self.select_none.connect("clicked", self._on_select_none)
        self.new_folder.connect("clicked", self._on_new_folder)
        self.close_button.connect("clicked", self._on_button_closed)
        self.help_button.connect("clicked", self._on_help_clicked)
        self.about_button.connect("clicked", self._on_about_clicked)
        self.show_hidden_button.connect("toggled", self._on_hidden_toggled)
        self.a_to_z_button.connect("toggled", self._on_sort_toggled)
        self.go_top_button.connect("clicked", self._go_to_top)

        self._adjustment = self.content_scroll.get_vadjustment()
        self._adjustment.connect("value-changed", self._update_go_top_button)

        self.search.connect("toggled", self._on_search_toggled)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", self._on_search_stopped)
        self.back.connect("clicked", self._on_back_clicked)

        places = PortfolioPlaces()
        places.connect("updated", self._on_places_updated)
        places.connect("removed", self._on_places_removed)
        self.places_box.add(places)

        self._move(PortfolioPlaces.PORTFOLIO_HOME_DIR)

    def _filter(self, model, row, data=None):
        path = model[row][self.PATH_COLUMN]
        text = self.search_entry.get_text()
        if not text:
            return True
        return text.lower() in os.path.basename(path).lower()

    def _sort_by_last_modified(self, path1, path2):
        st_mtime1 = os.path.getmtime(path1)
        st_mtime2 = os.path.getmtime(path2)

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

        row1_is_dir = os.path.isdir(path1)
        row2_is_dir = os.path.isdir(path2)

        if row1_is_dir and not row2_is_dir:
            return -1
        elif not row1_is_dir and row2_is_dir:
            return 1

        if self.a_to_z_button.props.active:
            return self._sort_by_a_to_z(path1, path2)
        else:
            return self._sort_by_last_modified(path1, path2)

    def _select_all(self):
        self._force_select = True
        self.selection.select_all()
        self._force_select = False

    def _unselect_all(self):
        self._force_select = True
        self.selection.unselect_all()
        self._force_select = False

    def _select_row(self, row):
        self._force_select = True
        self.selection.select_iter(row)
        self._force_select = False

    def _get_selection(self):
        model, treepaths = self.selection.get_selected_rows()
        selection = [
            (
                model[treepath][self.PATH_COLUMN],
                Gtk.TreeRowReference.new(model, treepath),
            )
            for treepath in treepaths
        ]
        return selection

    def _remove_row(self, ref):
        if ref is None or not ref.valid():
            return

        treepath = ref.get_path()
        treepath = self.sorted.convert_path_to_child_path(treepath)
        treepath = self.filtered.convert_path_to_child_path(treepath)

        self.liststore.remove(self.liststore.get_iter(treepath))

    def _populate(self, directory):
        self._worker = PortfolioLoadWorker(
            directory, self.show_hidden_button.props.active
        )
        self._worker.connect("started", self._on_load_started)
        self._worker.connect("updated", self._on_load_updated)
        self._worker.connect("finished", self._on_load_finished)
        self._worker.start()

    def _paste(self, Worker, to_paste):
        directory = self._history[self._index]

        self._worker = Worker(to_paste, directory)
        self._worker.connect("started", self._on_paste_started)
        self._worker.connect("updated", self._on_paste_updated)
        self._worker.connect("finished", self._on_paste_finished)
        self._worker.connect("failed", self._on_paste_failed)
        self._worker.start()

    def _get_row(self, model, treepath):
        return model.get_iter(treepath)

    def _get_path(self, model, treepath):
        return model[model.get_iter(treepath)][self.PATH_COLUMN]

    def _go_to_selection(self):
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        self.treeview.set_cursor_on_cell(
            treepath, self.name_column, self.name_cell, False
        )
        self.treeview.scroll_to_cell(treepath, None, False, 0, 0)

    def _go_to_top(self, *args):
        if len(self.sorted) >= 1:
            self.treeview.scroll_to_cell(0, None, True, 0, 0)

    def _move(self, path, navigating=False):
        self._clean_popups()

        if path is None:
            return
        elif os.path.isdir(path):
            self._update_history(path, navigating)
            self._populate(path)
        else:
            Gio.AppInfo.launch_default_for_uri(f"file://{path}")

    def _reset_to_path(self, path):
        self._history = []
        self._index = -1
        self._move(path, False)

    def _refresh(self):
        self._move(self._history[self._index], True)

    def _switch_to_navigation_mode(self):
        self.selection.set_mode(Gtk.SelectionMode.NONE)

    def _switch_to_selection_mode(self):
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)

    def _notify(self, description, on_confirm, on_cancel, autoclose, data):
        self._clean_popups()

        self._popup = PortfolioPopup(
            description, on_confirm, on_cancel, autoclose, data
        )
        self.popup_box.add(self._popup)
        self._popup.props.reveal_child = True

    def _find_icon(self, path):
        if os.path.isdir(path):
            return "folder-symbolic"
        else:
            return "text-x-generic-symbolic"

    def _clean_workers(self):
        del self._worker
        self._worker = None

    def _clean_popups(self):
        if self._popup is None:
            return
        self._popup.destroy()
        self._popup = None

    def _update_mode(self):
        count = self.selection.count_selected_rows()
        if count == 0:
            self._switch_to_navigation_mode()

    def _update_history(self, path, navigating):
        if path not in self._history or not navigating:
            del self._history[self._index + 1 :]
            self._history.append(path)
            self._index += 1

    def _update_all(self):
        self._update_search()
        self._update_content_stack()
        self._update_navigation()
        self._update_navigation_tools()
        self._update_selection()
        self._update_selection_tools()
        self._update_action_stack()
        self._update_tools_stack()
        self._update_menu()
        self._update_go_top_button()

    def _update_search(self):
        sensitive = not self._editing and not self._busy
        self.search.props.sensitive = sensitive
        self.search_entry.sensitive = sensitive

    def _update_content_stack(self):
        if self._busy:
            return
        elif len(self.sorted) == 0:
            self.content_stack.set_visible_child(self.placeholder_box)
        else:
            self.content_stack.set_visible_child(self.content_box)

    def _update_navigation(self):
        count = self.selection.count_selected_rows()
        selected = count >= 1

        if selected or self._busy:
            self.previous.props.sensitive = False
            self.next.props.sensitive = False
            return

        self.previous.props.sensitive = True if self._index > 0 else False
        self.next.props.sensitive = (
            True if len(self._history) - 1 > self._index else False
        )

    def _update_selection(self):
        sensitive = not self._editing and not self._busy

        self.select_all.props.sensitive = sensitive
        self.select_none.props.sensitive = sensitive

    def _update_action_stack(self):
        count = self.selection.count_selected_rows()
        selected = count >= 1
        child = self.selection_box if selected else self.navigation_box
        self.action_stack.set_visible_child(child)

    def _update_tools_stack(self):
        count = self.selection.count_selected_rows()
        selected = count >= 1
        child = self.selection_tools if selected else self.navigation_tools
        self.tools_stack.set_visible_child(child)

    def _update_selection_tools(self):
        count = self.selection.count_selected_rows()
        sensitive = count >= 1 and not self._editing and not self._busy

        self.delete.props.sensitive = sensitive
        self.cut.props.sensitive = sensitive
        self.copy.props.sensitive = sensitive

        self._update_rename()

    def _update_navigation_tools(self):
        count = self.selection.count_selected_rows()
        selected = count >= 1
        to_paste = len(self._to_cut) >= 1 or len(self._to_copy) >= 1
        self.paste.props.sensitive = not selected and to_paste and not self._busy
        self.new_folder.props.sensitive = not selected and not self._busy

    def _update_rename(self):
        count = self.selection.count_selected_rows()
        sensitive = count == 1 and not self._editing and not self._busy
        self.rename.props.sensitive = sensitive

    def _update_directory_title(self):
        directory = self._history[self._index]
        name = os.path.basename(directory)
        self.headerbar.set_title(name)

    def _update_filter(self):
        self.filtered.refilter()
        self._update_content_stack()

        self._search_delay_handler_id = 0
        return GLib.SOURCE_REMOVE

    def _update_menu(self):
        self.menu_box.props.sensitive = not self._busy

    def _update_go_top_button(self, *args):
        alloc = self.get_allocation()
        reveal = self._adjustment.get_value() > (alloc.height / 2) and not self._editing
        self.go_top_revealer.props.reveal_child = reveal

    def _reset_search(self):
        self.search.set_active(False)
        self.search_entry.set_text("")
        self.search.grab_focus()

    def _on_load_started(self, worker, directory):
        self._busy = True

        self._update_directory_title()
        self._reset_search()

        self.liststore.clear()

        self.loading_label.set_text(_("Loading"))
        self.loading_bar.set_fraction(0.0)
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_load_updated(self, worker, directory, found, index, total):
        for name, path in found:
            icon = self._find_icon(path)
            self.liststore.append([icon, name, path])
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_load_finished(self, worker, directory):
        self._busy = False
        self._clean_workers()

        self._go_to_top()
        self._update_all()

    def _on_load_failed(self, worker, directory):
        self._clean_workers()

    def _on_clicked(self, treeview, event):
        result = self.treeview.get_path_at_pos(event.x, event.y)
        if result is None:
            return
        treepath, column, x, y = result
        self._last_clicked = treepath

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

    def _on_selection_changed(self, selection):
        self._update_all()
        self._update_mode()

    def _on_go_previous(self, button):
        self._index -= 1
        self._move(self._history[self._index], True)

    def _on_go_next(self, button):
        self._index += 1
        self._move(self._history[self._index], True)

    def _on_search_toggled(self, button):
        toggled = self.search.get_active()
        self.search_box.props.search_mode_enabled = toggled

    def _on_search_changed(self, entry):
        if self._search_delay_handler_id != 0:
            GLib.Source.remove(self._search_delay_handler_id)
        self._search_delay_handler_id = GLib.timeout_add(
            self.SEARCH_DELAY, self._update_filter
        )

    def _on_search_stopped(self, entry):
        self._reset_search()

    def _on_rename_clicked(self, button):
        self.name_cell.props.editable = True
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        self.treeview.set_cursor_on_cell(
            treepath, self.name_column, self.name_cell, True
        )

    def _on_rename_started(self, cell_name, treepath, data=None):
        self._editing = True

        self._update_search()
        self._update_selection()
        self._update_selection_tools()
        self._update_go_top_button()

    def _on_rename_updated(self, cell_name, treepath, new_name, data=None):
        directory = self._history[self._index]
        new_path = os.path.join(directory, new_name)
        old_path = self._get_path(self.sorted, treepath)

        if new_path == old_path:
            self._on_rename_finished()
            return

        try:
            # respect empty folders
            if os.path.exists(new_path):
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
                True,
                None,
            )
            self._on_rename_clicked(None)
            return

        # remove this folder from history
        self._history = [
            path for path in self._history if not path.startswith(old_path)
        ]

        # take the user to the new position
        self._on_rename_finished()
        self._go_to_selection()

    def _on_rename_finished(self, *args):
        self.name_cell.props.editable = False
        self._editing = False
        self._update_all()

    def _on_delete_clicked(self, button):
        selection = self._get_selection()
        count = len(selection)

        if count == 1:
            name = os.path.basename(selection[0][0])
        else:
            name = _("these %d files") % count

        description = _("Delete %s?") % name

        self._notify(
            description,
            self._on_delete_confirmed,
            self._on_popup_closed,
            False,
            selection,
        )

    def _on_cut_clicked(self, button):
        selection = self._get_selection()
        count = len(selection)

        self._to_cut = selection
        self._to_copy = []

        if count == 1:
            name = os.path.basename(selection[0][0])
            description = _("%s will be moved") % name
        else:
            description = _("%d files will be moved") % count

        self._notify(description, None, None, True, None)

        self._unselect_all()
        self._update_mode()

    def _on_copy_clicked(self, button):
        selection = self._get_selection()
        count = len(selection)

        self._to_copy = selection
        self._to_cut = []

        if count == 1:
            name = os.path.basename(selection[0][0])
            description = _("%s will be copied") % name
        else:
            description = _("%d files will be copied") % count

        self._notify(description, None, None, True, None)

        self._unselect_all()
        self._update_mode()

    def _on_paste_clicked(self, button):
        to_paste = self._to_copy if self._to_copy else self._to_cut
        Worker = PortfolioCopyWorker if self._to_copy else PortfolioCutWorker

        directory = self._history[self._index]
        should_warn = any(
            [
                os.path.dirname(path) != directory
                and os.path.exists(os.path.join(directory, os.path.basename(path)))
                for path, ref in to_paste
            ]
        )

        if not should_warn:
            self._paste(Worker, to_paste)
            return

        self._notify(
            _("Files will be overwritten, proceed?"),
            self._on_paste_confirmed,
            self._on_popup_closed,
            False,
            (to_paste, Worker),
        )

    def _on_paste_confirmed(self, button, popup, data):
        to_paste, Worker = data
        self._clean_popups()
        self._paste(Worker, to_paste)

    def _on_paste_started(self, worker, total):
        self._busy = True

        self.loading_label.set_text(_("Pasting"))
        self.loading_bar.set_fraction(0.0)
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_paste_updated(self, worker, path, overwritten, index, total):
        # XXX this approach won't allow me to put stat info in liststore
        if not overwritten:
            icon = self._find_icon(path)
            name = os.path.basename(path)
            self.liststore.append([icon, name, path])

        self.loading_bar.set_fraction((index + 1) / total)

    def _on_paste_finished(self, worker, total):
        self._busy = False
        self._clean_workers()

        self._to_cut = []
        self._to_copy = []

        self._unselect_all()

        self._update_all()
        self._update_mode()

    def _on_paste_failed(self, worker, path):
        self._busy = False
        self._clean_workers()

        self._to_cut = []
        self._to_copy = []

        name = os.path.basename(path)
        self.loading_description.set_text(_("Could not paste %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_delete_confirmed(self, button, popup, selection):
        self._clean_popups()

        # clean history entries from deleted paths
        directory = self._history[self._index]
        self._history = [
            path
            for path in self._history
            if not path.startswith(directory) or path == directory
        ]

        self._worker = PortfolioDeleteWorker(selection)
        self._worker.connect("started", self._on_delete_started)
        self._worker.connect("updated", self._on_delete_updated)
        self._worker.connect("finished", self._on_delete_finished)
        self._worker.connect("failed", self._on_delete_failed)
        self._worker.start()

    def _on_delete_started(self, worker, total):
        self._busy = True

        self.loading_label.set_text(_("Deleting"))
        self.loading_bar.set_fraction(0.0)
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_delete_updated(self, worker, path, ref, index, total):
        self._remove_row(ref)
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_delete_finished(self, worker, total):
        self._busy = False
        self._clean_workers()

        self._unselect_all()
        self._update_all()
        self._update_mode()

    def _on_delete_failed(self, worker, path):
        self._busy = False
        self._clean_workers()

        name = os.path.basename(path)
        self.loading_description.set_text(_("Could not delete %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_popup_closed(self, button, popup, data):
        self._clean_popups()

    def _on_button_closed(self, button):
        self.loading_description.set_text("")
        self._unselect_all()
        self._update_all()
        self._update_mode()

    def _on_select_all(self, button):
        self._select_all()
        self._update_mode()

    def _on_select_none(self, button):
        self._unselect_all()

    def _on_new_folder(self, button):
        directory = self._history[self._index]
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
                True,
                None,
            )
            return

        self._switch_to_selection_mode()

        icon = self._find_icon(path)
        row = self.liststore.append([icon, folder_name, path])
        result, row = self.filtered.convert_child_iter_to_iter(row)
        result, row = self.sorted.convert_child_iter_to_iter(row)

        self._select_row(row)

        self._go_to_selection()
        self._on_rename_clicked(None)

    def _on_row_activated(self, treeview, treepath, treecolumn, data=None):
        if self._dont_activate is True:
            self._dont_activate = False
            return
        if self.selection.get_mode() == Gtk.SelectionMode.NONE:
            path = self._get_path(self.sorted, treepath)
            self._move(path)

    def _on_places_updated(self, button, path):
        self._reset_to_path(path)

    def _on_places_removed(self, button, path):
        directory = self._history[self._index]
        if not directory.startswith(path):
            return
        self._reset_to_path(PortfolioPlaces.PORTFOLIO_HOME_DIR)

    def _on_help_clicked(self, button):
        Gio.AppInfo.launch_default_for_uri("https://github.com/tchx84/Portfolio", None)

    def _on_about_clicked(self, button):
        self.deck.set_visible_child(self.about_box)

    def _on_back_clicked(self, button):
        self.deck.set_visible_child(self.app_box)

    def _on_long_pressed(self, gesture, x, y):
        if self.selection.get_mode() != Gtk.SelectionMode.MULTIPLE:
            self._switch_to_selection_mode()
            treepath = self.treeview.get_path_at_pos(x, y)[0]
            self.selection.select_path(treepath)
            # because of the custom selection rules, is not guaranteed
            # that this will actually be selected so always update mode.
            self._update_mode()

    def _on_hidden_toggled(self, button):
        self._refresh()

    def _on_sort_toggled(self, button):
        self._refresh()
