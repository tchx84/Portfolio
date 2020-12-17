# places.py
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

from gi.repository import Gio, Gtk, GObject


class PortfolioPlaces(Gtk.Box):
    __gtype_name__ = 'PortfolioPlaces'

    __gsignals__ = {
        'updated': (GObject.SIGNAL_RUN_LAST, None, (str,)),
    }

    def __init__(self, **kargs):
        super().__init__(**kargs)
        self._setup()

    def _setup(self):
        self.props.orientation = Gtk.Orientation.VERTICAL
        self.props.visible = True

        self._manager = Gio.VolumeMonitor.get()
        self._manager.connect('mount-added', self._on_mount_added)
        self._manager.connect('mount-removed', self._on_mount_removed)

        self._add_button("Home", os.path.expanduser('~'))
        for mount in self._manager.get_mounts():
            self._add_button(mount.get_name(), mount.get_root().get_path())

    def _add_button(self, name, path):
        button = Gtk.ModelButton()
        button.props.text = name
        button.props.centered = True
        button.props.visible = True
        button.connect('clicked', self._on_button_clicked)

        context = button.get_style_context()
        context.add_class('menu-item')

        setattr(button, 'path', path)
        self.add(button)

    def _on_button_clicked(self, button):
        self.emit('updated', button.path)

    def _on_mount_added(self, monitor, mount):
        self._add_button(mount.get_name(), mount.get_root().get_path())

    def _on_mount_removed(self, monitor, mount):
        for button in self.get_children():
            if button.path == mount.get_root().get_path():
                button.destroy()
