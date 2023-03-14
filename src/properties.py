# properties.py
#
# Copyright 2023 Martin Abente Lahaye
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

from gi.repository import GObject, Gtk


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/properties.ui")
class PortfolioProperties(Gtk.Box):
    __gtype_name__ = "PortfolioProperties"

    property_name = Gtk.Template.Child()
    property_location = Gtk.Template.Child()
    property_type = Gtk.Template.Child()
    property_size = Gtk.Template.Child()
    property_created = Gtk.Template.Child()
    property_modified = Gtk.Template.Child()
    property_accessed = Gtk.Template.Child()
    property_permissions_owner = Gtk.Template.Child()
    property_permissions_group = Gtk.Template.Child()
    property_permissions_others = Gtk.Template.Child()
    property_owner = Gtk.Template.Child()
    property_group = Gtk.Template.Child()

    def __init__(self, worker, **kwargs):
        super().__init__(**kwargs)
        self._worker = worker
        self._setup()

    def _setup(self):
        self._worker.bind_property(
            "name",
            self.property_name,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "location",
            self.property_location,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "type",
            self.property_type,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "size",
            self.property_size,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "created",
            self.property_created,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "modified",
            self.property_modified,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "accessed",
            self.property_accessed,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "permissions_owner",
            self.property_permissions_owner,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "permissions_group",
            self.property_permissions_group,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "permissions_others",
            self.property_permissions_others,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "owner",
            self.property_owner,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._worker.bind_property(
            "group",
            self.property_group,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
