# places.py
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

import os

from gi.repository import GLib, Gtk, GObject, Handy

from . import logger
from .place import PortfolioPlace
from .devices import PortfolioDevices
from .translation import gettext as _


class PortfolioPlaces(Gtk.Stack):
    __gtype_name__ = "PortfolioPlaces"

    __gsignals__ = {
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "removing": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "removed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "unlock": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    FLATPAK_INFO = os.path.join(os.path.abspath(os.sep), ".flatpak-info")
    PORTFOLIO_SYSTEM_DIR = os.path.abspath(os.sep)
    PORTFOLIO_SYSTEM_DIR_FLATPAK = os.path.join(os.path.abspath(os.sep), "run", "host")
    PORTFOLIO_HOME_DIR = os.environ.get("PORTFOLIO_HOME_DIR", os.path.expanduser("~"))

    XDG_DOWNLOAD = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
    XDG_DOCUMENTS = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
    XDG_PICTURES = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
    XDG_MUSIC = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
    XDG_VIDEOS = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)

    XDG_TRASH = "Trash"
    XDG_TRASH_NAME = _("Trash")

    HOST_PERMISSION = ["host"]
    HOME_PERMISSION = ["host", "home"]
    DOWNLOAD_PERMISSION = ["host", "home", "xdg-download"]
    DOCUMENTS_PERMISSION = ["host", "home", "xdg-documents"]
    PICTURES_PERMISSION = ["host", "home", "xdg-pictures"]
    MUSIC_PERMISSION = ["host", "home", "xdg-music"]
    VIDEOS_PERMISSION = ["host", "home", "xdg-videos"]
    TRASH_PERMISSION = ["host", "home"]

    def __init__(self, **kargs):
        super().__init__(**kargs)
        self._setup()

    def _setup(self):
        self.props.visible = True
        self.props.transition_type = Gtk.StackTransitionType.CROSSFADE

        self._permissions = None

        self._devices = PortfolioDevices()
        self._devices.connect("added", self._on_device_added)
        self._devices.connect("removed", self._on_device_removed)
        self._devices.connect("encrypted-added", self._on_encrypted_added)

        # begin UI structure

        self._groups_box = Gtk.Box()
        self._groups_box.props.expand = True
        self._groups_box.props.visible = True
        self._groups_box.props.orientation = Gtk.Orientation.VERTICAL

        self._message_box = Gtk.Box()
        self._message_box.props.expand = True
        self._message_box.props.visible = True
        self._message_box.props.orientation = Gtk.Orientation.VERTICAL

        self._places_group = Handy.PreferencesGroup()
        self._places_group.props.title = _("Places")
        self._places_group.props.visible = True

        self._devices_group = Handy.PreferencesGroup()
        self._devices_group.props.title = _("Devices")
        self._devices_group.props.visible = True
        self._devices_group.get_style_context().add_class("devices-group")

        # places

        if self._has_permission_for(self.HOME_PERMISSION):
            self._add_place(
                self._places_group,
                "user-home-symbolic",
                _("Home"),
                self.PORTFOLIO_HOME_DIR,
            )
        if self._has_permission_for(self.DOWNLOAD_PERMISSION) and self.XDG_DOWNLOAD:
            self._add_place(
                self._places_group,
                "folder-download-symbolic",
                os.path.basename(self.XDG_DOWNLOAD),
                self.XDG_DOWNLOAD,
            )
        if self._has_permission_for(self.DOCUMENTS_PERMISSION) and self.XDG_DOCUMENTS:
            self._add_place(
                self._places_group,
                "folder-documents-symbolic",
                os.path.basename(self.XDG_DOCUMENTS),
                self.XDG_DOCUMENTS,
            )
        if self._has_permission_for(self.PICTURES_PERMISSION) and self.XDG_PICTURES:
            self._add_place(
                self._places_group,
                "folder-pictures-symbolic",
                os.path.basename(self.XDG_PICTURES),
                self.XDG_PICTURES,
            )
        if self._has_permission_for(self.MUSIC_PERMISSION) and self.XDG_MUSIC:
            self._add_place(
                self._places_group,
                "folder-music-symbolic",
                os.path.basename(self.XDG_MUSIC),
                self.XDG_MUSIC,
            )
        if self._has_permission_for(self.VIDEOS_PERMISSION) and self.XDG_VIDEOS:
            self._add_place(
                self._places_group,
                "folder-videos-symbolic",
                os.path.basename(self.XDG_VIDEOS),
                self.XDG_VIDEOS,
            )
        if self._has_permission_for(self.TRASH_PERMISSION):
            self._add_place(
                self._places_group,
                "user-trash-symbolic",
                self.XDG_TRASH_NAME,
                self.XDG_TRASH,
            )

        # static devices

        if self._has_permission_for(self.HOST_PERMISSION):
            self._add_place(
                self._devices_group,
                "drive-harddisk-ieee1394-symbolic",
                _("System"),
                self.PORTFOLIO_SYSTEM_DIR,
            )

        if self._has_permission_for(self.HOST_PERMISSION) and self._is_flatpak():
            self._add_place(
                self._devices_group,
                "drive-harddisk-ieee1394-symbolic",
                _("Host"),
                self.PORTFOLIO_SYSTEM_DIR_FLATPAK,
            )

        self._groups_box.add(self._places_group)
        self._groups_box.add(self._devices_group)

        # no places message

        message = Gtk.Label()
        message.props.expand = True
        message.props.visible = True
        message.props.label = _("No places found")
        message.get_style_context().add_class("no-places")

        self._message_box.add(message)

        # finalize UI structure

        self.add_named(self._groups_box, "groups")
        self.add_named(self._message_box, "message")

        # dynamic devices

        self._devices.scan()

        # update visibility

        self._update_stack_visibility()
        self._update_places_group_visibility()
        self._update_device_group_visibility()

    def _update_stack_visibility(self):
        groups = len(self._places_group.get_children())
        devices = len(self._devices_group.get_children())

        if not groups and not devices:
            self.set_visible_child_name("message")
        else:
            self.set_visible_child_name("groups")

    def _update_places_group_visibility(self):
        visible = len(self._places_group.get_children()) >= 1
        self._places_group.props.visible = visible

    def _update_device_group_visibility(self):
        visible = len(self._devices_group.get_children()) >= 1
        self._devices_group.props.visible = visible

    def _get_permissions(self):
        if self._permissions is not None:
            return self._permissions

        info = GLib.KeyFile()
        info.load_from_file(self.FLATPAK_INFO, GLib.KeyFileFlags.NONE)
        permissions = info.get_value("Context", "filesystems")

        if permissions is not None:
            self._permissions = set(permissions.split(";"))
        else:
            self._permissions = set()

        return self._permissions

    def _is_flatpak(self):
        return os.path.exists(self.FLATPAK_INFO)

    def _has_permission_for(self, required):
        # not using flatpak, so access to all
        if not self._is_flatpak():
            return True

        permissions = self._get_permissions()
        required = set(required)
        negated = set([f"!{r}" for r in required])

        if required.intersection(permissions):
            return True
        if negated.intersection(permissions):
            return False

        return False

    def _add_place(self, group, icon, name, path):
        place = PortfolioPlace()
        place.set_icon_name(icon)
        place.set_title(name)
        place.set_subtitle(path)
        place.path = path
        place.props.activatable = True
        place.connect("activated", self._on_place_activated)
        group.add(place)

        return place

    def _find_place_by_device_uuid(self, group, device):
        for place in group.get_children():
            if place.uuid == device.uuid:
                return place
        return None

    def _filter_device(self, device):
        if device.mount_point is None:
            logger.debug(f"No mount point for {device}")
            return False
        if not os.access(device.mount_point, os.R_OK):
            logger.debug(f"No permissions for {device}")
            return True
        if device.mount_point == "/" and self._is_flatpak():
            logger.debug(f"Skip root directory for {device}")
            return True

        return False

    def _update_place_from_device(self, place, device):
        if place is None:
            return

        if self._filter_device(device):
            place.destroy()
            return

        place.path = device.mount_point
        place.set_title(device.label)
        place.set_subtitle(device.mount_point)

    def _on_place_activated(self, place):
        if place.path is not None:
            self.emit("updated", place.path)
        elif place.encrypted is not None:
            self.emit("unlock", place.encrypted)
        elif place.device is not None:
            place.device.mount(self._on_insert_finished)

    def _on_insert_finished(self, device, success):
        self.emit("updated", device.mount_point)

    def _on_encrypted_added(self, devices, encrypted):
        logger.debug(f"added {encrypted}")

        place = self._add_place(
            self._devices_group,
            "system-lock-screen-symbolic",
            encrypted.get_friendly_label(),
            None,
        )

        place.uuid = encrypted.uuid
        place.encrypted = encrypted

        place.eject.props.visible = True
        place.eject.connect("clicked", self._on_encrypted_eject, encrypted)

    def _on_device_added(self, devices, device):
        logger.debug(f"added {device}")

        if self._filter_device(device):
            return

        place = self._add_place(
            self._devices_group,
            "drive-removable-media-symbolic",
            device.label,
            device.mount_point,
        )

        place.uuid = device.uuid
        place.device = device
        place.eject.props.visible = True
        place.eject.connect("clicked", self._on_eject, device)

        device.connect("updated", self._on_device_updated)

        self._update_place_from_device(place, device)
        self._update_stack_visibility()
        self._update_device_group_visibility()

    def _on_device_removed(self, devices, device):
        logger.debug(f"removed {device}")
        place = self._find_place_by_device_uuid(self._devices_group, device)

        if place is not None:
            place.destroy()

        self.emit("removed", device.mount_point)

    def _on_device_updated(self, device):
        logger.debug(f"updated {device}")
        place = self._find_place_by_device_uuid(self._devices_group, device)
        self._update_place_from_device(place, device)

    def _on_eject(self, button, device):
        logger.debug(f"eject {device}")
        self.emit("removing", device.mount_point)
        device.eject(self._on_eject_finished)

    def _on_eject_finished(self, device, success):
        logger.debug(f"eject finished {device} {success}")
        if success:
            self._on_device_removed(None, device)
        else:
            self.emit("failed", device.mount_point)

    def _on_encrypted_eject(self, button, encrypted):
        encrypted.eject(self._on_encrypted_eject_finished)

    def _on_encrypted_eject_finished(self, encrypted, success):
        pass
