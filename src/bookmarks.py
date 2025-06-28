# devices.py
#
# Copyright 2025 Jason Beetham
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

from gi.repository import Gio, GLib, GObject

from . import logger
from . import utils
import json, os


class PortfolioBookmarks(GObject.GObject):
    __gtype_name__ = "PortfolioBookmarks"

    __gsignals__ = {
        "toggle-bookmark": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "add-bookmark": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "remove-bookmark": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.connect("toggle-bookmark", self._toggle_bookmark)

        self.bookmarked = {}
        self._portfolio_config_path = os.path.join(GLib.get_user_config_dir(), "portfolio")
        self._bookmark_path = os.path.join(self._portfolio_config_path, "bookmarks")

        try:
            with open(self._bookmark_path, 'r') as f:
                data = f.read()
                if not data is None:
                    bookmarked = json.loads(data)
                    for val in bookmarked:
                        if type(val) is not str:
                            bookmarked = []
                            break

                    for path in bookmarked:
                        self._add_bookmark(path)

        except (json.JSONDecodeError, OSError, IOError):
            self.bookmarked = {}

    def _add_bookmark(self, path):
        if path not in self.bookmarked:
            name = os.path.basename(path)
            self.bookmarked[path] = 0 # Python Hashsets are limited?
            self.emit("add-bookmark", path)

    def _delete_bookmark(self, path):
        if path in self.bookmarked:
            self.bookmarked.pop(path)
            self.emit("remove-bookmark", path)

    def is_bookmarked(self, path):
        return path in self.bookmarked

    def _save_bookmarks(self):
        os.makedirs(self._portfolio_config_path, exist_ok = True)
        with open(self._bookmark_path, 'w') as f:
            paths = [bookmark for bookmark in self.bookmarked]
            json.dump(paths, f)

    def _toggle_bookmark(self, button, path):
        if self.is_bookmarked(path):
            self._delete_bookmark(path)
        else:
            self._add_bookmark(path)
        self._save_bookmarks()

