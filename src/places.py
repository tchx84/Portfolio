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

from gi.repository import GLib, Gio, Gtk, GObject, Handy

from . import logger
from .place import PortfolioPlace
from .translation import gettext as _


class PortfolioPlaces(Gtk.Stack):
    __gtype_name__ = "PortfolioPlaces"

    __gsignals__ = {
        "updated": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "removing": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "removed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
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

        self._manager = Gio.VolumeMonitor.get()
        self._manager.connect("mount-added", self._on_mount_added)
        self._manager.connect("mount-removed", self._on_mount_removed)

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

        # devices

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

        for mount in self._manager.get_mounts():
            if mount.get_root().get_path() not in [
                self.PORTFOLIO_SYSTEM_DIR,
                self.PORTFOLIO_HOME_DIR,
            ]:
                self._add_place(
                    self._devices_group,
                    "drive-removable-media-symbolic",
                    mount.get_name(),
                    mount.get_root().get_path(),
                    mount,
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

    def _add_place(self, group, icon, name, path, mount=None):
        place = PortfolioPlace()
        place.set_icon_name(icon)
        place.set_title(name)
        place.set_subtitle(path)
        place.path = path
        place.mount = mount
        place.eject.props.visible = mount is not None
        place.eject.connect("clicked", self._on_eject, place)
        place.connect("activated", self._on_place_activated)

        group.add(place)

    def _remove_place(self, group, mount):
        for place in group.get_children():
            if place.path == mount.get_root().get_path():
                self.emit("removed", place.path)
                place.destroy()

    def _on_place_activated(self, place):
        self.emit("updated", place.path)

    def _on_mount_added(self, monitor, mount):
        self._add_place(
            self._devices_group,
            "drive-removable-media-symbolic",
            mount.get_name(),
            mount.get_root().get_path(),
            mount,
        )
        self._update_stack_visibility()
        self._update_device_group_visibility()

    def _on_mount_removed(self, monitor, mount):
        self._remove_place(self._devices_group, mount)
        self._update_stack_visibility()
        self._update_device_group_visibility()

    def _on_eject(self, button, place):
        mount = place.mount

        if mount.can_eject():
            method = mount.eject
            finish = mount.eject_finish
        elif mount.can_unmount():
            method = mount.unmount
            finish = mount.unmount_finish

        method(Gio.MountUnmountFlags.NONE, None, self._on_eject_finished, finish)
        place.props.sensitive = False
        self.emit("removing", place.path)

    def _on_eject_finished(self, mount, task, finish):
        try:
            finish(task)
        except Exception as e:
            logger.debug(e)
