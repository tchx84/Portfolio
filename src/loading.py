# loading.py
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

from gi.repository import Gtk


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/loading.ui")
class PortfolioLoading(Gtk.Box):
    __gtype_name__ = "PortfolioLoading"

    title = Gtk.Template.Child()
    progress = Gtk.Template.Child()
    description = Gtk.Template.Child()
    details = Gtk.Template.Child()

    def update(self, title=None, progress=None, description=None, details=None):
        if title is not None:
            self.title.set_text(title)
        if progress is not None:
            self.progress.set_fraction(progress)
        if description is not None:
            self.description.set_text(description)
        if details is not None:
            self.details.set_text(details)

        self.description.props.visible = True if self.description.props.label else False
        self.details.props.visible = True if self.details.props.label else False

    def pulse(self):
        self.progress.pulse()

    def clean(self):
        self.update("", 0.0, "", "")
