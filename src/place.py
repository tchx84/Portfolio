# place.py
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

from gi.repository import Gtk, Handy


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/place.ui")
class PortfolioPlace(Handy.ActionRow):
    __gtype_name__ = "PortfolioPlace"

    eject = Gtk.Template.Child()
    insert = Gtk.Template.Child()
    unlock = Gtk.Template.Child()
    mount = None
    path = ""
    uuid = ""
