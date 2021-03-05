# translation.py
#
# Copyright 2021 Clayton Craft
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

from . import logger

gettext = lambda msg: msg


def init(localedir):
    global gettext

    try:
        import locale

        gettext = locale.gettext
        locale.bindtextdomain("portfolio", localedir)
        locale.textdomain("portfolio")
    except AttributeError:
        logger.debug("Using fallback gettext module")
        import gettext as _gettext

        gettext = _gettext.gettext
        _gettext.bindtextdomain("portfolio", localedir)
        _gettext.textdomain("portfolio")
