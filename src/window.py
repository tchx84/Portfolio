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
import shutil

from pathlib import Path
from gi.repository import Gtk, Gio, GObject, GLib, Handy

from gi.repository.Handy import Deck, ApplicationWindow, HeaderBar, SearchBar

from .row import PortfolioRow
from .popup import PortfolioPopup
from .placeholder import PortfolioPlaceholder
from .worker import PortfolioCutWorker
from .worker import PortfolioCopyWorker
from .worker import PortfolioDeleteWorker
from .worker import PortfolioLoadWorker
from .places import PortfolioPlaces


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/window.ui")
class PortfolioWindow(ApplicationWindow):
    __gtype_name__ = "PortfolioWindow"

    list = Gtk.Template.Child()
    previous = Gtk.Template.Child()
    next = Gtk.Template.Child()
    search = Gtk.Template.Child()
    back = Gtk.Template.Child()
    rename = Gtk.Template.Child()
    delete = Gtk.Template.Child()
    cut = Gtk.Template.Child()
    copy = Gtk.Template.Child()
    paste = Gtk.Template.Child()
    menu = Gtk.Template.Child()
    select_all = Gtk.Template.Child()
    select_none = Gtk.Template.Child()
    new_folder = Gtk.Template.Child()
    loading_label = Gtk.Template.Child()
    loading_bar = Gtk.Template.Child()
    loading_description = Gtk.Template.Child()
    close_button = Gtk.Template.Child()
    help_button = Gtk.Template.Child()
    about_button = Gtk.Template.Child()

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
    about_box = Gtk.Template.Child()
    close_box = Gtk.Template.Child()
    close_tools = Gtk.Template.Child()
    deck = Gtk.Template.Child()
    headerbar = Gtk.Template.Child()
    headerbar_stack = Gtk.Template.Child()
    overlay = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()

    def _setup(self):
        Handy.init()

        self._popup = None
        self._worker = None
        self._busy = False
        self._editing = False
        self._to_load = []
        self._to_copy = []
        self._to_cut = []
        self._history = []
        self._index = -1

        self.deck.connect("notify::visible-child", self._on_deck_child_changed)

        placeholder = PortfolioPlaceholder()
        placeholder.show_all()

        self.list.set_sort_func(self._sort)
        self.list.set_filter_func(self._filter)
        self.list.connect("selected-rows-changed", self._on_rows_selection_changed)
        self.list.connect("row-activated", self._on_row_activated)
        self.list.set_placeholder(placeholder)
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)

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

        self.search.connect("toggled", self._on_search_toggled)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", self._on_search_stopped)
        self.back.connect("clicked", self._on_back_clicked)

        places = PortfolioPlaces()
        places.connect("updated", self._on_places_updated)
        self.places_box.add(places)

        self._move(os.path.expanduser("~"))

    def _filter(self, row):
        text = self.search_entry.get_text()
        if not text:
            return True
        return text.lower() in os.path.basename(row.path.lower())

    def _sort(self, row1, row2):
        row1_is_dir = os.path.isdir(row1.path)
        row2_is_dir = os.path.isdir(row2.path)

        if row1_is_dir and not row2_is_dir:
            return -1
        elif not row1_is_dir and row2_is_dir:
            return 1

        path1 = row1.path.lower()
        path2 = row2.path.lower()

        if path1 < path2:
            return -1
        elif path1 > path2:
            return 1

        return 0

    def _populate(self, directory):
        self._worker = PortfolioLoadWorker(directory)
        self._worker.connect("started", self._on_load_started)
        self._worker.connect("updated", self._on_load_updated)
        self._worker.connect("finished", self._on_load_finished)
        self._worker.connect("failed", self._on_load_failed)
        self._worker.start()

    def _add_row(self, path):
        row = PortfolioRow(path)
        row.connect("rename-started", self._on_rename_started)
        row.connect("rename-updated", self._on_rename_updated)
        row.connect("rename-finished", self._on_rename_finished)
        row.connect("rename-failed", self._on_rename_failed)
        row.connect("activate-selection-mode", self._on_activated_selection_mode)
        row.props.selectable = False
        return row

    def _move(self, path, navigating=False):
        if path is None:
            return
        elif os.path.isdir(path):
            self._populate(path)
            self._update_history(path, navigating)
        else:
            Gio.AppInfo.launch_default_for_uri(f"file://{path}")

    def _refresh(self):
        self._move(self._history[self._index], True)

    def _switch_to_navigation_mode(self):
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)

    def _switch_to_selection_mode(self):
        self.list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

    def _notify(self, description, on_confirm, on_cancel, autoclose, data):
        if self._popup is not None:
            self._popup.destroy()

        self._popup = PortfolioPopup(
            description, on_confirm, on_cancel, autoclose, data
        )
        self.popup_box.add(self._popup)
        self._popup.props.reveal_child = True

    def _update_mode(self):
        rows = self.list.get_selected_rows()
        if not rows:
            self._switch_to_navigation_mode()

    def _update_history(self, path, navigating):
        if path not in self._history or not navigating:
            del self._history[self._index + 1 :]
            self._history.append(path)
            self._index += 1

    def _update_all(self):
        self._update_search()
        self._update_navigation()
        self._update_navigation_tools()
        self._update_selection()
        self._update_selection_tools()
        self._update_action_stack()
        self._update_tools_stack()

    def _update_search(self):
        sensitive = not self._editing and not self._busy
        self.search.props.sensitive = sensitive
        self.search_entry.props.sensitive = sensitive

    def _update_navigation(self):
        rows = self.list.get_selected_rows()
        selected = len(rows) >= 1

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
        rows = self.list.get_selected_rows()
        selected = len(rows) >= 1
        child = self.selection_box if selected else self.navigation_box
        self.action_stack.set_visible_child(child)

    def _update_tools_stack(self):
        rows = self.list.get_selected_rows()
        selected = len(rows) >= 1
        child = self.selection_tools if selected else self.navigation_tools
        self.tools_stack.set_visible_child(child)

    def _update_selection_tools(self):
        rows = self.list.get_selected_rows()
        sensitive = len(rows) >= 1 and not self._editing and not self._busy

        self.delete.props.sensitive = sensitive
        self.cut.props.sensitive = sensitive
        self.copy.props.sensitive = sensitive

        self._update_rename()

    def _update_navigation_tools(self):
        rows = self.list.get_selected_rows()
        selected = len(rows) >= 1
        to_paste = len(self._to_cut) >= 1 or len(self._to_copy) >= 1
        self.paste.props.sensitive = not selected and to_paste and not self._busy
        self.new_folder.props.sensitive = not selected and not self._busy

    def _update_rename(self):
        rows = self.list.get_selected_rows()
        sensitive = len(rows) == 1 and not self._editing and not self._busy
        self.rename.props.sensitive = sensitive

    def _update_directory_title(self):
        directory = self._history[self._index]
        name = os.path.basename(directory)
        self.headerbar.set_title(name)

    def _reset_search(self):
        self.search.set_active(False)
        self.search_entry.set_text("")
        self.list.invalidate_filter()
        self.search.grab_focus()

    def _on_menu_started(self, button):
        pass

    def _on_load_started(self, worker, directory):
        self._busy = True
        self._to_load = []

        self._update_directory_title()
        self._reset_search()

        for row in self.list.get_children():
            row.destroy()

        self.loading_label.set_text("Loading")
        self.loading_bar.set_fraction(0.0)
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_load_updated(self, worker, directory, path, name, index, total):
        row = self._add_row(path)
        self._to_load.append(row)
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_load_finished(self, worker, directory):
        self._busy = False

        # remove functions to speedup
        self.list.set_sort_func(None)
        self.list.set_filter_func(None)

        for row in self._to_load:
            self.list.add(row)

        self.list.set_sort_func(self._sort)
        self.list.set_filter_func(self._filter)

        self._to_load = []
        self._update_all()

        self.content_stack.set_visible_child(self.content_box)

    def _on_load_failed(self, worker, directory):
        pass

    def _on_rows_selection_changed(self, widget):
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
        self.list.invalidate_filter()

    def _on_search_stopped(self, entry):
        self._reset_search()

    def _on_rename_clicked(self, button):
        row = self.list.get_selected_rows()[-1]
        row.rename()

    def _on_rename_started(self, row):
        self._editing = True

        self._update_search()
        self._update_selection()
        self._update_selection_tools()

    def _on_rename_updated(self, row):
        # remove this folder from history
        self._history = [
            path for path in self._history if not path.startswith(row.path)
        ]

    def _on_rename_finished(self, row):
        self._editing = False

        self.search.grab_focus()
        self.list.unselect_all()

        row.props.selectable = False

        self._update_all()

    def _on_rename_failed(self, row, name):
        self._notify(f"{name} already exists.", None, self._on_popup_closed, True, None)

    def _on_delete_clicked(self, button):
        rows = self.list.get_selected_rows()

        if len(rows) == 1:
            name = os.path.basename(rows[0].path)
        else:
            name = f"these {len(rows)} files"

        description = f"Delete {name}?"

        self._notify(
            description, self._on_delete_confirmed, self._on_popup_closed, False, rows
        )

    def _on_cut_clicked(self, button):
        rows = self.list.get_selected_rows()
        self._to_cut = [row.path for row in rows]
        self._to_copy = []

        if len(rows) == 1:
            name = os.path.basename(rows[0].path)
        else:
            name = f"{len(rows)} files"

        self._notify(f"{name} will be moved.", None, None, True, None)

        self.list.unselect_all()
        self._update_mode()

    def _on_copy_clicked(self, button):
        rows = self.list.get_selected_rows()
        self._to_copy = [row.path for row in rows]
        self._to_cut = []

        if len(rows) == 1:
            name = os.path.basename(rows[0].path)
        else:
            name = f"{len(rows)} files"

        self._notify(f"{name} will be copied.", None, None, True, None)

        self.list.unselect_all()
        self._update_mode()

    def _on_paste_clicked(self, button):
        directory = self._history[self._index]

        if self._to_cut:
            self._worker = PortfolioCutWorker(self._to_cut, directory)
        elif self._to_copy:
            self._worker = PortfolioCopyWorker(self._to_copy, directory)

        self._worker.connect("started", self._on_paste_started)
        self._worker.connect("updated", self._on_paste_updated)
        self._worker.connect("finished", self._on_paste_finished)
        self._worker.connect("failed", self._on_paste_failed)
        self._worker.start()

    def _on_paste_started(self, worker, total):
        self._busy = True

        self.loading_label.set_text("Pasting")
        self.loading_bar.set_fraction(0.0)
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_paste_updated(self, worker, index, total):
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_paste_finished(self, worker, total):
        self._busy = False

        # remove functions to speedup
        self.list.set_sort_func(None)
        self.list.set_filter_func(None)

        directory = self._history[self._index]
        paths = self._to_copy if self._to_copy else self._to_cut
        for path in paths:
            name = os.path.basename(path)
            new_path = os.path.join(directory, name)
            row = self._add_row(new_path)
            self.list.add(row)

        self.list.set_sort_func(self._sort)
        self.list.set_filter_func(self._filter)

        self._to_cut = []
        self._to_copy = []
        self.list.unselect_all()

        self.content_stack.set_visible_child(self.content_box)

        self._update_all()
        self._update_mode()

    def _on_paste_failed(self, worker, path):
        self._busy = False
        self._to_cut = []
        self._to_copy = []

        name = os.path.basename(path)
        self.loading_description.set_text(f"Could not paste {name}.")

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_delete_confirmed(self, button, popup, rows):
        self._popup.destroy()

        to_delete = [row.path for row in rows]

        # clean history entries from deleted paths
        directory = self._history[self._index]
        self._history = [
            path
            for path in self._history
            if not path.startswith(directory) or path == directory
        ]

        self._worker = PortfolioDeleteWorker(to_delete)
        self._worker.connect("started", self._on_delete_started)
        self._worker.connect("updated", self._on_delete_updated)
        self._worker.connect("finished", self._on_delete_finished)
        self._worker.connect("failed", self._on_delete_failed)
        self._worker.start()

    def _on_delete_started(self, worker, total):
        self._busy = True

        self.loading_label.set_text("Deleting")
        self.loading_bar.set_fraction(0.0)
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_delete_updated(self, worker, index, total):
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_delete_finished(self, worker, total):
        self._busy = False

        # remove functions to speedup
        self.list.set_sort_func(None)
        self.list.set_filter_func(None)

        rows = self.list.get_selected_rows()
        for row in rows:
            row.destroy()

        self.list.set_sort_func(self._sort)
        self.list.set_filter_func(self._filter)

        self.list.unselect_all()

        self.content_stack.set_visible_child(self.content_box)

        self._update_all()
        self._update_mode()

    def _on_delete_failed(self, worker, path):
        self._busy = False

        name = os.path.basename(path)
        self.loading_description.set_text(f"Could not delete {name}.")

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_popup_closed(self, button, popup, data):
        self._popup.destroy()
        self._popup = None

    def _on_button_closed(self, button):
        self.list.unselect_all()

        self._update_all()
        self._update_mode()
        self._refresh()

        self.content_stack.set_visible_child(self.content_box)

    def _on_select_all(self, button):
        # Make sure all rows are selectable
        for row in self.list.get_children():
            row.props.selectable = True
        self.list.select_all()
        self._update_mode()

    def _on_select_none(self, button):
        self.list.unselect_all()
        self._update_mode()
        for row in self.list.get_children():
            row.props.selectable = False

    def _on_new_folder(self, button):
        directory = self._history[self._index]

        counter = 1
        folder_name = "New Folder"
        while os.path.exists(os.path.join(directory, folder_name)):
            folder_name = folder_name.split("(")[0]
            folder_name = f"{folder_name}({counter})"
            counter += 1

        path = os.path.join(directory, folder_name)

        Path(path).mkdir(parents=False, exist_ok=True)

        row = self._add_row(path)
        row.props.selectable = True
        self._switch_to_selection_mode()
        self.list.add(row)
        self.list.select_row(row)
        row.rename()

    def _on_activated_selection_mode(self, row):
        if self._editing:
            return
        self._switch_to_selection_mode()
        row.preselect()

        # XXX ugh...
        row.props.selectable = True
        self.list.select_row(row)
        row.props.selectable = False

    def _on_row_activated(self, list, row):
        rows = self.list.get_selected_rows()
        mode = self.list.get_selection_mode()

        # In navigation mode we move or activate
        if mode == Gtk.SelectionMode.NONE:
            self._move(row.path)

        if self._editing:
            return

        # In selection mode we handle selections
        if row in rows:
            self.list.unselect_row(row)
            row.props.selectable = False
        else:
            row.props.selectable = True
            self.list.select_row(row)
            row.deselect()

    def _on_places_updated(self, button, path):
        self._history = []
        self._index = -1
        self._move(path, False)

    def _on_help_clicked(self, button):
        Gio.AppInfo.launch_default_for_uri("https://github.com/tchx84/Portfolio", None)

    def _on_about_clicked(self, button):
        self.deck.set_visible_child(self.about_box)

    def _on_back_clicked(self, button):
        self.deck.set_visible_child(self.overlay)

    def _on_deck_child_changed(self, check, child):
        child = self.deck.get_visible_child()
        if child == self.about_box:
            self.headerbar.set_title("About")
            self.headerbar_stack.set_visible_child(self.back)
        else:
            self._update_directory_title()
            self.headerbar_stack.set_visible_child(self.search)
