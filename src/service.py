# service.py
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

import os

from gi.repository import Gio


class PortfolioService:
    def __init__(self, app):
        self._app = app
        self._dbus_id = None
        self._name_id = Gio.bus_own_name(
            Gio.BusType.SESSION,
            os.environ.get("PORTFOLIO_SERVICE_NAME", "org.freedesktop.FileManager1"),
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            self._on_name_acquired,
            self._on_name_lost,
        )

    def __del__(self):
        self.shutdown()

    def _on_bus_acquired(self, connection, name):
        xml = (
            Gio.resources_lookup_data(
                "/dev/tchx84/Portfolio/org.freedesktop.FileManager1.xml",
                Gio.ResourceLookupFlags.NONE,
            )
            .get_data()
            .decode("utf-8")
        )
        info = Gio.DBusNodeInfo.new_for_xml(xml)

        activation_id = connection.register_object(
            "/org/freedesktop/FileManager1", info.interfaces[0], self._on_called
        )

        assert activation_id > 0

    def _on_name_acquired(self, connection, name):
        pass

    def _on_name_lost(self, connection, name):
        pass

    def _on_called(self, connection, sender, path, iface, method, params, invocation):
        paths, _ = params

        if len(paths) == 0:
            invocation.return_value(None)
            return

        last_path = paths[-1]

        if method == "ShowItemProperties":
            self._app.show_properties(last_path)
        else:
            self._app.open_path(last_path)

        invocation.return_value(None)

    def shutdown(self):
        Gio.bus_unown_name(self._name_id)
