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
from gi.repository import Gtk, Gio, GObject

from .row import PortfolioRow
from .popup import PortfolioPopup
from .placeholder import PortfolioPlaceholder
from .worker import PortfolioCutWorker
from .worker import PortfolioCopyWorker
from .worker import PortfolioDeleteWorker


@Gtk.Template(resource_path='/dev/tchx84/Portfolio/window.ui')
class PortfolioWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'PortfolioWindow'

    list = Gtk.Template.Child()
    previous = Gtk.Template.Child()
    next = Gtk.Template.Child()
    search = Gtk.Template.Child()
    rename = Gtk.Template.Child()
    delete = Gtk.Template.Child()
    cut = Gtk.Template.Child()
    copy = Gtk.Template.Child()
    paste = Gtk.Template.Child()
    menu = Gtk.Template.Child()
    select_all = Gtk.Template.Child()
    select_none = Gtk.Template.Child()
    new_folder = Gtk.Template.Child()

    directory_box = Gtk.Template.Child()
    directory = Gtk.Template.Child()
    search_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    popup_box = Gtk.Template.Child()
    action_stack = Gtk.Template.Child()
    tools_stack = Gtk.Template.Child()
    navigation_box = Gtk.Template.Child()
    selection_box = Gtk.Template.Child()
    selection_tools = Gtk.Template.Child()
    navigation_tools = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()

    def _setup(self):
        builder = Gtk.Builder.new_from_resource('/dev/tchx84/Portfolio/menu.ui')
        self.menu.set_menu_model(builder.get_object('menu'))

        self._popup = None
        self._worker = None
        self._deleting = False
        self._pasting = False
        self._editing = False
        self._to_copy = []
        self._to_cut = []
        self._history = []
        self._index = -1

        placeholder = PortfolioPlaceholder()
        placeholder.show_all()

        self.list.set_sort_func(self._sort)
        self.list.set_filter_func(self._filter)
        self.list.connect('selected-rows-changed', self._on_rows_selection_changed)
        self.list.set_placeholder(placeholder)
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.previous.connect('clicked', self._on_go_previous)
        self.next.connect('clicked', self._on_go_next)
        self.rename.connect('toggled', self._on_rename_toggled)
        self.delete.connect('clicked', self._on_delete_clicked)
        self.cut.connect('clicked', self._on_cut_clicked)
        self.copy.connect('clicked', self._on_copy_clicked)
        self.paste.connect('clicked', self._on_paste_clicked)
        self.select_all.connect('clicked', self._on_select_all)
        self.select_none.connect('clicked', self._on_select_none)
        self.new_folder.connect('clicked', self._on_new_folder)

        self.search.connect('toggled', self._on_search_toggled)
        self.search_entry.connect('search-changed', self._on_search_changed)
        self.search_entry.connect('stop-search', self._on_search_stopped)

        self._populate(os.path.expanduser('~'))

    def _find_icon(self, path):
        if os.path.isdir(path):
            return 'inode-directory-symbolic'
        else:
            return 'folder-documents-symbolic'

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

    def _populate(self, directory, navigating=False):
        for row in self.list.get_children():
            row.destroy()

        for file_name in os.listdir(directory):
            # XXX ignore these until I can add some filters
            if file_name.startswith('.'):
                continue
            path = os.path.join(directory, file_name)
            icon_name = self._find_icon(path)
            self._add_row(path, icon_name, file_name)

        if directory not in self._history or not navigating:
            del self._history[self._index + 1:]
            self._history.append(directory)
            self._index += 1

        self._update_navigation()
        self._update_navigation_tools()
        self.directory.set_text(directory)
        self._reset_search()

    def _add_row(self, path, icon_name, file_name):
        row = PortfolioRow(path, icon_name, file_name)
        # The order matters
        row.connect('edit-done', self._on_row_edited)
        row.connect('activate-selection-mode', self._on_activated_selection_mode)
        row.connect_after('clicked', self._on_row_clicked)
        self.list.add(row)
        return row

    def _move(self, path, navigating=False):
        if path is None:
            return
        elif os.path.isdir(path):
            self._populate(path, navigating)
        else:
            Gio.AppInfo.launch_default_for_uri(f'file://{path}')

    def _refresh(self):
        self._move(self._history[self._index], True)

    def _switch_to_navigation_mode(self):
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)

    def _switch_to_selection_mode(self):
        self.list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

    def _update_mode(self):
        rows = self.list.get_selected_rows()
        if not rows:
            self._switch_to_navigation_mode()

    def _update_search(self):
        sensitive = not self.rename.props.active and not self._pasting and not self._deleting
        self.search.props.sensitive = sensitive
        self.search_entry.props.sensitive = sensitive

    def _update_navigation(self):
        rows = self.list.get_selected_rows()
        selected = len(rows) >= 1

        if selected or self._pasting or self._deleting:
            self.previous.props.sensitive = False
            self.next.props.sensitive = False
            return

        self.previous.props.sensitive = True if self._index > 0 else False
        self.next.props.sensitive = True if len(self._history) - 1 > self._index else False

    def _update_multi_selection(self):
        sensitive = not self.rename.props.active

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
        sensitive = len(rows) >= 1 and not self.rename.props.active

        self.delete.props.sensitive = sensitive
        self.cut.props.sensitive = sensitive
        self.copy.props.sensitive = sensitive

        self._update_rename()

    def _update_navigation_tools(self):
        rows = self.list.get_selected_rows()
        selected = len(rows) >= 1
        to_paste = len(self._to_cut) >= 1 or len(self._to_copy) >= 1
        self.paste.props.sensitive = (not selected and to_paste and not self._pasting and not self._deleting)
        self.new_folder.props.sensitive = (not selected and not self._pasting and not self._deleting)

    def _update_rename(self):
        rows = self.list.get_selected_rows()
        single = len(rows) == 1
        self.rename.props.sensitive = single

    def _reset_search(self):
        self.search.set_active(False)
        self.search_entry.set_text('')
        self.list.invalidate_filter()
        self.search.grab_focus()

    def _on_rows_selection_changed(self, widget):
        self._update_navigation()
        self._update_navigation_tools()
        self._update_selection_tools()
        self._update_action_stack()
        self._update_tools_stack()
        self._update_mode()

    def _on_go_previous(self, button):
        self._index -= 1
        self._move(self._history[self._index], True)

    def _on_go_next(self, button):
        self._index += 1
        self._move(self._history[self._index], True)

    def _on_search_toggled(self, button):
        toggled = self.search.get_active()
        if toggled:
            self.stack.set_visible_child(self.search_box)
            self.search_entry.grab_focus()
        else:
            self.stack.set_visible_child(self.directory_box)
            self._reset_search()

    def _on_search_changed(self, entry):
        self.list.invalidate_filter()

    def _on_search_stopped(self, entry):
        self._reset_search()
        
    def _on_rename_toggled(self, button):
        row = self.list.get_selected_rows()[-1]
        active = self.rename.get_active()
        sensitive = not active

        # XXX find a better way to disallow selection
        for child in self.list.get_children():
            if child  == row:
                continue
            child.props.sensitive = sensitive

        self._update_search()
        self._update_multi_selection()
        self._update_selection_tools()

        if active:
            self._editing = True
            self._switch_to_selection_mode()
            row.new_name.grab_focus()
        else:
            self._editing = False
            new_name = row.new_name.get_text()
            directory = os.path.dirname(row.path)
            new_path = os.path.join(directory, new_name)
            os.rename(row.path, new_path)
            self.search.grab_focus()
            self.list.unselect_all()

        row.toggle_mode()

    def _on_delete_clicked(self, button):
        rows = self.list.get_selected_rows()

        if len(rows) == 1:
            name = os.path.basename(rows[0].path)
        else:
            name = f'these {len(rows)} files'

        description = f'Delete {name}?'

        self._popup = PortfolioPopup(
            description,
            self._on_delete_confirmed,
            self._on_popup_closed,
            rows)
        self.popup_box.add(self._popup)
        self._popup.props.reveal_child = True

    def _on_cut_clicked(self, button):
        rows = self.list.get_selected_rows()
        self._to_cut = [row.path for row in rows]
        self._to_copy = []

        if len(rows) == 1:
            name = os.path.basename(rows[0].path)
        else:
            name = f'{len(rows)} files'

        popup = PortfolioPopup(
            f"{name} will be moved",
            None,
            None,
            None)
        self.popup_box.add(popup)
        popup.props.reveal_child = True

        self.list.unselect_all()
        self._update_mode()

    def _on_copy_clicked(self, button):
        rows = self.list.get_selected_rows()
        self._to_copy = [row.path for row in rows]
        self._to_cut = []

        if len(rows) == 1:
            name = os.path.basename(rows[0].path)
        else:
            name = f'{len(rows)} files'

        popup = PortfolioPopup(
            f"{name} will be copied",
            None,
            None,
            None)
        self.popup_box.add(popup)
        popup.props.reveal_child = True

        self.list.unselect_all()
        self._update_mode()

    def _on_paste_clicked(self, button):
        directory = self._history[self._index]

        if self._to_cut:
            self._worker = PortfolioCutWorker(self._to_cut, directory)
        elif self._to_copy:
            self._worker = PortfolioCopyWorker(self._to_copy, directory)

        self._worker.connect('started', self._on_paste_started)
        self._worker.connect('updated', self._on_paste_updated)
        self._worker.connect('finished', self._on_paste_finished)
        self._worker.start()

    def _on_paste_started(self, worker, total):
        self._pasting = True

        self._popup = PortfolioPopup(
            f"Preparing to paste {total} files...",
            None,
            self._on_popup_closed,
            None)
        self._popup.cancel_button.props.sensitive = False
        self.popup_box.add(self._popup)
        self._popup.props.reveal_child = True

        self._update_search()
        self._update_navigation()
        self._update_navigation_tools()

    def _on_paste_updated(self, worker, index, total):
        self._popup.set_description( f"Pasting {index + 1} of {total} files")
        self._refresh()

    def _on_paste_finished(self, worker, total):
        self._pasting = False

        description = f"{total} files"
        if total == 1:
            description = f"{total} file"

        self._popup.set_description( f"Successfully pasted {description}")
        self._popup.cancel_button.props.sensitive = True

        self._to_cut = []
        self._to_copy = []

        self._update_search()
        self._update_navigation()
        self._update_navigation_tools()

        self.list.unselect_all()
        self._update_mode()

    def _on_delete_confirmed(self, button, popup, rows):
        self._popup.destroy()

        to_delete = [row.path for row in rows]

        self._worker = PortfolioDeleteWorker(to_delete)
        self._worker.connect('started', self._on_delete_started)
        self._worker.connect('updated', self._on_delete_updated)
        self._worker.connect('finished', self._on_delete_finished)
        self._worker.start()

    def _on_delete_started(self, worker, total):
        self._deleting = True

        self._popup = PortfolioPopup(
            f"Preparing to delete {total} files...",
            None,
            self._on_popup_closed,
            None)
        self._popup.cancel_button.props.sensitive = False
        self.popup_box.add(self._popup)
        self._popup.props.reveal_child = True

        self._update_search()
        self._update_navigation()
        self._update_navigation_tools()

    def _on_delete_updated(self, worker, index, total):
        self._popup.set_description( f"Deleting {index + 1} of {total} files")
        self._refresh()

    def _on_delete_finished(self, worker, total):
        self._deleting = False

        description = f"{total} files"
        if total == 1:
            description = f"{total} file"

        self._popup.set_description( f"Successfully deleted {description}")
        self._popup.cancel_button.props.sensitive = True

        self._update_search()
        self._update_navigation()
        self._update_navigation_tools()

        self.list.unselect_all()
        self._update_mode()

    def _on_popup_closed(self, button, popup, data):
        self._popup.destroy()
        self._popup = None

    def _on_select_all(self, button):
        # Make sure all rows are selectable
        for row in self.list.get_children():
            row.props.selectable = True
        self.list.select_all()
        self._update_mode()

    def _on_select_none(self, button):
        self.list.unselect_all()
        self._update_mode()

    def _on_new_folder(self, button):
        directory = self._history[self._index]

        counter = 1
        folder_name = "New Folder"
        while os.path.exists(os.path.join(directory, folder_name)):
            folder_name = folder_name.split('(')[0]
            folder_name = f'{folder_name}({counter})'
            counter += 1

        path = os.path.join(directory, folder_name)

        Path(path).mkdir(parents=False, exist_ok=True)
        icon_name = self._find_icon(path)

        row = self._add_row(path, icon_name, folder_name)
        self._switch_to_selection_mode()
        self.list.select_row(row)
        self.rename.props.active = True

    def _on_row_edited(self, button):
        self.rename.props.active = False

    def _on_activated_selection_mode(self, row):
        self._switch_to_selection_mode()

    def _on_row_clicked(self, row):
        rows = self.list.get_selected_rows()
        mode =  self.list.get_selection_mode()

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
