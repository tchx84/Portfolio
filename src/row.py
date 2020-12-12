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

from gi.repository import GLib, Gtk, GObject


@Gtk.Template(resource_path='/dev/tchx84/Portfolio/row.ui')
class PortfolioRow(Gtk.ListBoxRow):
    __gtype_name__ = 'PortfolioRow'

    __gsignals__ = {
        'edit-done': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'activate-selection-mode': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'clicked': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    icon = Gtk.Template.Child()
    name = Gtk.Template.Child()
    new_name = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, path, icon_name, text):
        super().__init__()
        self.path = path
        self.icon.set_from_icon_name(icon_name, Gtk.IconSize.INVALID)
        self.name.set_text(text)
        self.select_gesture = Gtk.GestureLongPress.new(self)

        # The order matters
        self.new_name.connect('activate', self._on_enter_pressed)
        self.select_gesture.connect('pressed', self._on_long_pressed)
        self.connect_after('button-release-event', self._on_button_released)

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
        self.emit('activate-selection-mode')

    def _on_enter_pressed(self, entry):
        self.emit('edit-done')

    def _on_button_released(self, row, data=None):
        self.emit('clicked');
