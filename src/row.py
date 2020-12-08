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

from gi.repository import Gtk


@Gtk.Template(resource_path='/dev/tchx84/Portfolio/row.ui')
class PortfolioRow(Gtk.ListBoxRow):
    __gtype_name__ = 'PortfolioRow'

    icon = Gtk.Template.Child()
    name = Gtk.Template.Child()
    new_name = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, list, path, icon_name, text):
        super().__init__()
        self.path = path
        self.icon.set_from_icon_name(icon_name, Gtk.IconSize.INVALID)
        self.name.set_text(text)

        self.select_gesture = Gtk.GestureLongPress.new(self)
        self.select_gesture.connect('pressed', self._on_long_pressed, list)
        self.select_gesture.connect_after('cancelled', self._on_cancelled, list)


    def delete(self):
        os.unlink(self.path)

    def set_rename_mode(self, mode=False):
        if mode is True:
            self.new_name.set_text(self.name.get_text())
            self.new_name.grab_focus()
            self.stack.set_visible_child(self.new_name)
        else:
            self.stack.set_visible_child(self.name)

            new_name = self.new_name.get_text()
            if self.name.get_text() == new_name:
                return

            directory = os.path.dirname(self.path)
            new_path = os.path.join(directory, new_name)

            os.rename(self.path, new_path)

            self.path = new_path
            self.name.set_text(new_name)

    def _on_long_pressed(self, gesture, x, y, list):
        self.props.activatable = False
        list.select_row(self)

    def _on_cancelled(self, gesture, data=None):
        self.props.activatable = True
