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

from gi.repository import Gtk, Gio, GObject

from .row import PortfolioRow
from .popup import PortfolioPopup
from .placeholder import PortfolioPlaceholder


@Gtk.Template(resource_path='/dev/tchx84/Portfolio/window.ui')
class PortfolioWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'PortfolioWindow'

    list = Gtk.Template.Child()
    previous = Gtk.Template.Child()
    next = Gtk.Template.Child()
    search = Gtk.Template.Child()
    rename = Gtk.Template.Child()
    delete = Gtk.Template.Child()
    menu = Gtk.Template.Child()
    select_all = Gtk.Template.Child()
    select_none = Gtk.Template.Child()


    directory_box = Gtk.Template.Child()
    directory = Gtk.Template.Child()
    search_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    popup_box = Gtk.Template.Child()
    action_stack = Gtk.Template.Child()
    navigation_box = Gtk.Template.Child()
    selection_box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()

    def _setup(self):
        builder = Gtk.Builder.new_from_resource('/dev/tchx84/Portfolio/menu.ui')
        self.menu.set_menu_model(builder.get_object('menu'))

        self._history = []
        self._index = -1

        placeholder = PortfolioPlaceholder()
        placeholder.show_all()

        self.list.set_filter_func(self._filter)
        self.list.connect('selected-rows-changed', self._on_row_selected)
        self.list.connect('row-activated', self._on_row_activated)
        self.list.set_placeholder(placeholder)
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.previous.connect('clicked', self._on_go_previous)
        self.next.connect('clicked', self._on_go_next)
        self.rename.connect('toggled', self._on_rename_toggled)
        self.delete.connect('clicked', self._on_delete_clicked)
        self.select_all.connect('clicked', self._on_select_all)
        self.select_none.connect('clicked', self._on_select_none)

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

    def _populate(self, directory, navigating=False):
        for row in self.list.get_children():
            row.destroy()

        for file_name in os.listdir(directory):
            path = os.path.join(directory, file_name)
            icon_name = self._find_icon(path)
            row = PortfolioRow(self.list, path, icon_name, file_name)
            self.list.add(row)

        if directory not in self._history or not navigating:
            del self._history[self._index + 1:]
            self._history.append(directory)
            self._index += 1

        self._update_navigation()
        self.directory.set_text(directory)
        self._reset_search()

    def _move(self, path, navigating=False):
        if path is None:
            return
        elif os.path.isdir(path):
            self._populate(path, navigating)
        else:
            Gio.AppInfo.launch_default_for_uri(f'file://{path}')

    def _update_navigation(self, override=None):
        if override is not None:
            self.previous.props.sensitive = override
            self.next.props.sensitive = override
            return

        self.previous.props.sensitive = True if self._index > 0 else False
        self.next.props.sensitive = True if len(self._history) - 1 > self._index else False

    def _reset_search(self):
        self.search.set_active(False)
        self.search_entry.set_text('')
        self.list.invalidate_filter()
        self.search.grab_focus()

    def _on_row_selected(self, widget):
        rows = self.list.get_selected_rows()
        selected = len(rows) >= 1
        single = len(rows) == 1

        self.rename.props.sensitive = single
        self.delete.props.sensitive = selected

        if selected:
            self.action_stack.set_visible_child(self.selection_box)
        else:
            self.action_stack.set_visible_child(self.navigation_box)

    def _on_row_activated(self, widget, row):
        if row is None:
            return
        self._move(row.path)

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
        toggled = self.rename.get_active()
        row = self.list.get_selected_row()
        deactivated = not toggled

        # XXX find a better way to disallow selection
        for child in self.list.get_children():
            if child  == row:
                continue
            child.props.sensitive = deactivated

        # Disallow navigation
        if toggled:
            self._update_navigation(deactivated)
        else:
            self._update_navigation()
            self.search.grab_focus()

        row.set_rename_mode(toggled)

    def _on_delete_clicked(self, button):
        rows = self.list.get_selected_rows()

        if len(rows) == 1:
            name = os.path.basename(rows[0].path)
        else:
            name = f'{len(rows)} files'

        description = f'{name} will be deleted'

        popup = PortfolioPopup(
            description,
            self.on_popup_confirmed,
            self.on_popup_cancelled,
            rows)
        popup.props.reveal_child = True

        self.popup_box.add(popup)

    def on_popup_confirmed(self, button, popup, rows):
        for row in rows:
            row.delete()
            row.destroy()
        popup.destroy()

    def on_popup_cancelled(self, button, popup, rows):
        popup.destroy()

    def _on_select_all(self, button):
        self.list.select_all()

    def _on_select_none(self, button):
        self.list.unselect_all()
