# cache.py
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


class PortfolioDevices(GObject.GObject):
    __gtype_name__ = "PortfolioDevices"

    def __init__(self):
        GObject.GObject.__init__(self)

        self._proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.UDisks2",
            "/org/freedesktop/UDisks2",
            "org.freedesktop.DBus.ObjectManager",
            None,
        )

    def get_devices(self):
        objects = self._proxy.call_sync(
            "GetManagedObjects",
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )

        # and so we begin...
        print(objects)


default_devices = PortfolioDevices()
default_devices.get_devices()
