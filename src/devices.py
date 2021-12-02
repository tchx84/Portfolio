# devices.py
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
        self._manager = self._get_proxy(
            "org.freedesktop.UDisks2",
            "/org/freedesktop/UDisks2",
            "org.freedesktop.DBus.ObjectManager",
        )

    def _get_proxy(self, bus_name, object_path, interface):
        return Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            None,
            bus_name,
            object_path,
            interface,
            None,
        )

    def _get_property(self, bus_name, object_path, interface, property):
        proxy = self._get_proxy(
            bus_name, object_path, "org.freedesktop.DBus.Properties"
        )
        return proxy.Get("(ss)", interface, property)

    def _get_string_from_array(self, array):
        return bytearray(array).replace(b"\x00", b"").decode("utf-8")

    def _get_drive(self, object_path):
        return self._get_proxy(
            "org.freedesktop.UDisks2",
            object_path,
            "org.freedesktop.UDisks2.Drive",
        )

    def _get_block(self, object_path):
        return self._get_proxy(
            "org.freedesktop.UDisks2",
            object_path,
            "org.freedesktop.UDisks2.Filesystem",
        )

    def _get_filesystem_property(self, object_path, property):
        return self._get_property(
            "org.freedesktop.UDisks2",
            object_path,
            "org.freedesktop.UDisks2.Filesystem",
            property,
        )

    def _get_block_property(self, object_path, property):
        return self._get_property(
            "org.freedesktop.UDisks2",
            object_path,
            "org.freedesktop.UDisks2.Block",
            property,
        )

    def _get_drive_property(self, object_path, property):
        return self._get_property(
            "org.freedesktop.UDisks2",
            object_path,
            "org.freedesktop.UDisks2.Drive",
            property,
        )

    def _mount_block(self, proxy):
        return proxy.Mount("(a{sv})", ({}))

    def _get_filesystem_mount_points(self, object_path):
        return [
            self._get_string_from_array(m)
            for m in self._get_filesystem_property(object_path, "MountPoints")
        ]

    def get_devices(self):
        objects = self._manager.GetManagedObjects()

        for object_path in objects.keys():
            if "org.freedesktop.UDisks2.Filesystem" in objects[object_path]:
                print(object_path)

                drive_object_path = self._get_block_property(object_path, "Drive")
                if drive_object_path == "/":
                    continue

                drive_removable = self._get_drive_property(
                    drive_object_path, "Removable"
                )
                if drive_removable is False:
                    continue

                mount_points = self._get_filesystem_mount_points(object_path)
                if mount_points:
                    continue

                try:
                    volume_proxy = self._get_block(object_path)
                    mount_point = self._mount_block(volume_proxy)
                    print(mount_point)
                except Exception as e:
                    print(e)


default_devices = PortfolioDevices()
default_devices.get_devices()
