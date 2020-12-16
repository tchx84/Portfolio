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
        'rename-started': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'rename-updated': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'rename-finished': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'rename-failed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'activate-selection-mode': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'clicked': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    PRESELECTED_STYLE_CLASS = 'preselected'

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


    def preselect(self):
        context = self.get_style_context()
        if not context.has_class(self.PRESELECTED_STYLE_CLASS):
           context.add_class(self.PRESELECTED_STYLE_CLASS)

    def deselect(self):
        context = self.get_style_context()
        if context.has_class(self.PRESELECTED_STYLE_CLASS):
            context.remove_class(self.PRESELECTED_STYLE_CLASS)

    def rename(self):
        self.new_name.set_text(self.name.get_text())
        self.stack.set_visible_child(self.new_name)
        self.new_name.grab_focus()
        self.emit('rename-started')

    def _on_long_pressed(self, gesture, x, y):
        self.emit('activate-selection-mode')

    def _on_enter_pressed(self, entry):
        directory = os.path.dirname(self.path)
        new_name = self.new_name.get_text()
        path = os.path.join(directory, new_name)

        try:
            os.rename(self.path, path)
            self.emit('rename-updated')
            self.name.set_text(new_name)
            self.path = path
            self.stack.set_visible_child(self.name)
            self.emit('rename-finished')
        except:
            self.emit('rename-failed', new_name)

    def _on_button_released(self, row, data=None):
        self.emit('clicked');
