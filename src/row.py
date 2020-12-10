# row.py
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

from gi.repository import GLib, Gtk


@Gtk.Template(resource_path='/dev/tchx84/Portfolio/row.ui')
class PortfolioRow(Gtk.ListBoxRow):
    __gtype_name__ = 'PortfolioRow'

    icon = Gtk.Template.Child()
    name = Gtk.Template.Child()
    new_name = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, list, path, icon_name, text):
        super().__init__()
        self._list = list
        self.path = path
        self.icon.set_from_icon_name(icon_name, Gtk.IconSize.INVALID)
        self.name.set_text(text)

        self.select_gesture = Gtk.GestureLongPress.new(self)
        self.select_gesture.connect('pressed', self._on_long_pressed)
        self._selected_id = self._list.connect_after('row-selected', self._on_row_selected)

    def destroy(self):
        self._list.disconnect(self._selected_id)
        self._list = None
        super().destroy()

    def toggle_mode(self):
        if self.stack.get_visible_child() == self.name:
            self.new_name.set_text(self.name.get_text())
            self.stack.set_visible_child(self.new_name)
        else:
            directory = os.path.dirname(self.path)
            self.name.set_text(self.new_name.get_text())
            self.path = os.path.join(directory, self.name.get_text())
            self.stack.set_visible_child(self.name)



    def _on_long_pressed(self, gesture, x, y):
        self._list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self._list.select_row(self)

    def _on_row_selected(self, widget, row):
        self.props.activatable = False
        rows = self._list.get_selected_rows()
        if not rows:
            self._list.set_selection_mode(Gtk.SelectionMode.NONE)
            self.props.activatable = True
