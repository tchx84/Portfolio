# cache.py
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

from gi.repository import GObject

from . import logger


class PortfolioCache(GObject.GObject):
    __gtype_name__ = "PortfolioCache"

    def __init__(self):
        super().__init__()
        self.deactivate()

    def has(self, key):
        if not self._active:
            return False

        return key in self._cache

    def retrieve(self, key):
        if not self.has(key):
            return None

        return self._cache[key]

    def store(self, key, value):
        if not self._active:
            return

        self._cache[key] = value

    def activate(self):
        logger.debug("cache activated")
        self._active = True
        self._cache = {}

    def deactivate(self):
        logger.debug("cache deactivated")
        self._active = False
        self._cache = {}


class cached(object):
    def __init__(self, function):
        self._function = function

    def __call__(self, *args, **kwargs):
        key = (self._function.__name__, args)

        if default_cache.has(key):
            return default_cache.retrieve(key)

        value = self._function(*args, **kwargs)
        default_cache.store(key, value)

        return value


default_cache = PortfolioCache()
