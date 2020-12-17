# main.py
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

import sys
import gi

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')

from gi.repository import Gdk, Gtk, Gio

from .window import PortfolioWindow
from .about import PortfolioAbout


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='dev.tchx84.Portfolio',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def _setup_actions(self):
        help_action = Gio.SimpleAction(name='help', state=None)
        help_action.connect('activate', self._on_help_activated)

        about_action = Gio.SimpleAction(name='about', state=None)
        about_action.connect('activate', self._on_about_activated)

        self.add_action(help_action)
        self.add_action(about_action)

    def _setup_styles(self):
        provider = Gtk.CssProvider();
        provider.load_from_resource('/dev/tchx84/Portfolio/main.css');
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),
            provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = PortfolioWindow(application=self)
            self._setup_actions()
            self._setup_styles()
        win.present()

    def _on_about_activated(self, action, data):
        about = PortfolioAbout()
        about.set_transient_for(self.props.active_window)
        about.present()

    def _on_help_activated(self, action, data):
        Gio.AppInfo.launch_default_for_uri('https://github.com/tchx84/Portfolio', None)


def main(version):
    app = Application()
    return app.run(sys.argv)
