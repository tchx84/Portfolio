# passphrase.py
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

import os

from gi.repository import Gtk, GObject

from . import logger
from .translation import gettext as _


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/passphrase.ui")
class PortfolioPassphrase(Gtk.Box):
    __gtype_name__ = "PortfolioPassphrase"

    __gsignals__ = {
        "unlocked": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    passphrase_entry = Gtk.Template.Child()
    passphrase_label = Gtk.Template.Child()
    passphrase_spinner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()

    def _setup(self):
        self._encrypted = None
        self.passphrase_entry.connect("activate", self._on_passphrase_activate)

    def _on_passphrase_activate(self, button):
        self.passphrase_entry.props.sensitive = False
        self.passphrase_label.props.visible = False
        self.passphrase_spinner.props.visible = True
        self.passphrase_spinner.props.spinning = True

        passphrase = self.passphrase_entry.get_text()
        self._encrypted.unlock(passphrase, self._on_places_unlock_finished)

    def _on_places_unlock_finished(self, device, encrypted, success):
        self.clean()

        if device is None:
            logger.debug(f"Failed to unlock {encrypted}")
        elif not os.access(device.mount_point, os.R_OK):
            logger.debug(f"No permissions for {device}")
        elif success is True:
            self._encrypted = None
            self.emit("unlocked", device.mount_point)
            return

        self._encrypted = encrypted
        self.passphrase_entry.grab_focus()
        self.passphrase_label.set_text(_("Sorry, that didn't work"))

    def clean(self):
        self.passphrase_entry.set_text("")
        self.passphrase_label.set_text("")
        self.passphrase_entry.props.sensitive = True
        self.passphrase_label.props.visible = True
        self.passphrase_spinner.props.visible = False
        self.passphrase_spinner.props.spinning = False

    def unlock(self, encrypted):
        self.clean()
        self._encrypted = encrypted
        self.passphrase_entry.grab_focus()
