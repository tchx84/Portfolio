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


class PortfolioDrive(GObject.GObject):
    __gtype_name__ = "PortfolioDrive"

    def __init__(self, object):
        GObject.GObject.__init__(self)

        self._object = object
        self._drive_proxy = object.get_interface("org.freedesktop.UDisks2.Drive")

        self.is_removable = self._get_drive_is_removable()

    def _get_drive_is_removable(self):
        return self._drive_proxy.get_cached_property("Removable")

    def eject(self):
        return self._drive_proxy.Eject("(a{sv})", ({}))


class PortfolioDevice(GObject.GObject):
    __gtype_name__ = "PortfolioDevice"

    __gsignals__ = {
        "updated": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, object):
        GObject.GObject.__init__(self)

        self._object = object
        self._block_proxy = object.get_interface("org.freedesktop.UDisks2.Block")

        self._filesystem_proxy = object.get_interface(
            "org.freedesktop.UDisks2.Filesystem"
        )
        self._filesystem_proxy.connect(
            "g-properties-changed", self._on_filesystem_changed
        )

        self.label = self._get_block_label()
        self.uuid = self._get_block_uuid()
        self.mount_point = self._get_filesystem_mount_point()

    def __repr__(self):
        return f"uuid:{self.uuid}, label:{self.label}, mount_point:{self.mount_point}"

    def _get_string_from_bytes(self, bytes):
        return bytearray(bytes).replace(b"\x00", b"").decode("utf-8")

    def _get_block_drive(self):
        return self._block_proxy.get_cached_property("Drive")

    def _get_block_label(self):
        for property in ["IdLabel", "IdUUID"]:
            if label := self._block_proxy.get_cached_property(property):
                return label.unpack()

        return None

    def _get_block_uuid(self):
        if uuid := self._block_proxy.get_cached_property("IdUUID"):
            return uuid.unpack()

        return None

    def _get_filesystem_mount_point(self):
        mount_points = [
            self._get_string_from_bytes(m)
            for m in self._filesystem_proxy.get_cached_property("MountPoints")
            if m
        ]

        if mount_points:
            return mount_points[0]

        return None

    def _on_filesystem_changed(self, proxy, new_properties, old_properties):
        properties = new_properties.unpack()
        if "MountPoints" in properties:
            self.mount_point = self._get_filesystem_mount_point()
            self.emit("updated")

    def mount(self):
        return self._filesystem_proxy.Mount("(a{sv})", ({}))

    def unmount(self):
        return self._filesystem_proxy.Unmount("(a{sv})", ({}))


class PortfolioDevices(GObject.GObject):
    __gtype_name__ = "PortfolioDevices"

    __gsignals__ = {
        "added": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "removed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._drives = {}
        self._devices = {}
        self._manager = None

        try:
            self._manager = self._get_manager_proxy()
        except Exception:
            return

        self._manager.connect("object-added", self._on_object_added)
        self._manager.connect("object-removed", self._on_object_removed)

    def _get_manager_proxy(self):
        return Gio.DBusObjectManagerClient.new_for_bus_sync(
            Gio.BusType.SYSTEM,
            Gio.DBusObjectManagerClientFlags.NONE,
            "org.freedesktop.UDisks2",
            "/org/freedesktop/UDisks2",
            None,
            None,
            None,
        )

    def _on_object_added(self, manager, object):
        self._add_object(object)

    def _on_object_removed(self, manager, object):
        self._remove_object(object)

    def _add_object(self, object):
        if drive := object.get_interface("org.freedesktop.UDisks2.Drive"):
            self._drives[drive.get_object_path()] = PortfolioDrive(object)
        elif device := object.get_interface("org.freedesktop.UDisks2.Filesystem"):
            self._devices[device.get_object_path()] = PortfolioDevice(object)
            self.emit("added", self._devices[device.get_object_path()])

    def _remove_object(self, object):
        if drive := object.get_interface("org.freedesktop.UDisks2.Drive"):
            del self._drives[drive.get_object_path()]
        elif device := object.get_interface("org.freedesktop.UDisks2.Filesystem"):
            self.emit("removed", self._devices[device.get_object_path()])
            del self._devices[device.get_object_path()]

    def get_devices(self):
        if self._manager is None:
            return
        for object in self._manager.get_objects():
            self._add_object(object)
