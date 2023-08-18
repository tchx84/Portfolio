# menu.py
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

from gi.repository import Gtk, Gio, GObject

from .settings import PortfolioSettings


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/menu.ui")
class PortfolioMenu(Gtk.Popover):
    __gtype_name__ = "PortfolioMenu"

    __gsignals__ = {
        "show-about": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    menu_box = Gtk.Template.Child()
    show_hidden_button = Gtk.Template.Child()
    a_to_z_button = Gtk.Template.Child()
    last_modified_button = Gtk.Template.Child()
    help_button = Gtk.Template.Child()
    about_button = Gtk.Template.Child()

    def __init__(self, settings):
        super().__init__()
        self._setup(settings)

    @property
    def is_sensitive(self):
        return self.menu_box.props.sensitive

    @is_sensitive.setter
    def is_sensitive(self, value):
        self.menu_box.props.sensitive = value

    def _setup(self, settings):
        self._settings = settings
        self._settings.connect("notify::show-hidden", self._on_show_hidden_changed)
        self._settings.connect("notify::sort-order", self._on_sort_order_changed)

        self._show_hidden_handler_id = self.show_hidden_button.connect(
            "toggled", self._on_show_hidden_toggled
        )
        self._sort_order_handler_id = self.a_to_z_button.connect(
            "toggled", self._on_sort_by_toggled
        )

        self.help_button.connect("clicked", self._on_help_clicked)
        self.about_button.connect("clicked", self._on_about_clicked)

        self._on_show_hidden_changed(self._settings, None)
        self._on_sort_order_changed(self._settings, None)

    def _on_show_hidden_changed(self, settings, data):
        GObject.signal_handler_block(
            self.show_hidden_button,
            self._show_hidden_handler_id,
        )

        self.show_hidden_button.props.active = self._settings.show_hidden

        GObject.signal_handler_unblock(
            self.show_hidden_button,
            self._show_hidden_handler_id,
        )

    def _on_sort_order_changed(self, settings, data):
        GObject.signal_handler_block(
            self.a_to_z_button,
            self._sort_order_handler_id,
        )

        if self._settings.sort_order == PortfolioSettings.ALPHABETICAL_ORDER:
            self.a_to_z_button.props.active = True
        else:
            self.last_modified_button.props.active = True

        GObject.signal_handler_unblock(
            self.a_to_z_button,
            self._sort_order_handler_id,
        )

    def _on_show_hidden_toggled(self, button):
        self._settings.show_hidden = self.show_hidden_button.props.active

    def _on_sort_by_toggled(self, button):
        if self.a_to_z_button.props.active:
            self._settings.sort_order = PortfolioSettings.ALPHABETICAL_ORDER
        else:
            self._settings.sort_order = PortfolioSettings.MODIFIED_TIME_ORDER

    def _on_help_clicked(self, button):
        Gio.AppInfo.launch_default_for_uri("https://github.com/tchx84/Portfolio", None)

    def _on_about_clicked(self, button):
        self.emit("show-about")
