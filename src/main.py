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

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio

from .window import PortfolioWindow
from .service import PortfolioService


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="dev.tchx84.Portfolio",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self._service = PortfolioService(self)

    def show_properties(self, path):
        self.activate()
        self.props.active_window.show_properties(path, force_page_switch=True)

    def open_path(self, path):
        self.activate()
        self.props.active_window.open(path, force_page_switch=True)

    def do_open(self, files, hint, data):
        self.open_path(files[0].get_path())

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = PortfolioWindow(application=self)
        win.present()


def main(version):
    app = Application()
    return app.run(sys.argv)
