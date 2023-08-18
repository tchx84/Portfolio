# settings.py
#
# Copyright 2021 Martin Abente Lahaye
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

from gi.repository import Gio, GObject


class PortfolioSettings(GObject.GObject):
    __gtype_name__ = "PortfolioSettings"

    SCHEMA = "dev.tchx84.Portfolio"
    ALPHABETICAL_ORDER = "alphabetical"
    MODIFIED_TIME_ORDER = "modified_time"

    def __init__(self):
        super().__init__()
        self._settings = None
        if Gio.SettingsSchemaSource.get_default().lookup(self.SCHEMA, False):
            self._settings = Gio.Settings(self.SCHEMA)

    @GObject.Property(type=bool, default=False)
    def show_hidden(self):
        if self._settings is None:
            return False
        return self._settings.get_boolean("show-hidden")

    @show_hidden.setter
    def show_hidden(self, value):
        if self._settings is None:
            return
        self._settings.set_boolean("show-hidden", value)

    @GObject.Property(type=str)
    def sort_order(self):
        if self._settings is None:
            return self.ALPHABETICAL_ORDER
        return self._settings.get_string("sort-order")

    @sort_order.setter
    def sort_order(self, value):
        if self._settings is None:
            return
        value = [self.ALPHABETICAL_ORDER, self.MODIFIED_TIME_ORDER].index(value)
        self._settings.set_enum("sort-order", value)
