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
        "bookmark_toggled": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._bookmarked = {}
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
            self._bookmarked = {}

        self.connect("bookmark_toggled", self._toggle_bookmark)

    def _add_bookmark(self, path):
        if path not in self._bookmarked:
            name = os.path.basename(path)
            self._bookmarked[path] = 0 # Python Hashsets are limited?

    def _delete_bookmark(self, path):
        if path in self._bookmarked:
            self._bookmarked.pop(path)

    def _is_bookmarked(self, path):
        return path in self._bookmarked

    def _toggle_bookmark(self, path):
        print("hello")
        if self._is_bookmarked(path):
            self._delete_bookmark(path)
        else:
            self._add_bookmark(path)

    def _save_bookmarks(self):
        os.makedirs(self._portfolio_config_path, exist_ok = True)
        with open(self._bookmark_path, 'w') as f:
            paths = [bookmark for bookmark in self._bookmarked]
            json.dump(paths, f)


