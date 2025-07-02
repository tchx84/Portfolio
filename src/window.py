# window.py
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

from .translation import gettext as _

from gi.repository import Adw, Gtk, GLib

from . import utils
from . import logger
from .popup import PortfolioPopup
from .worker import PortfolioCutWorker
from .worker import PortfolioCopyWorker
from .worker import PortfolioDeleteWorker
from .worker import PortfolioLoadWorker
from .worker import PortfolioOpenWorker
from .worker import PortfolioPropertiesWorker
from .worker import PortfolioRestoreTrashWorker
from .worker import PortfolioDeleteTrashWorker
from .worker import PortfolioSendTrashWorker
from .worker import PortfolioLoadTrashWorker
from .places import PortfolioPlaces
from .properties import PortfolioProperties
from .about import PortfolioAbout
from .passphrase import PortfolioPassphrase
from .placeholder import PortfolioPlaceholder
from .loading import PortfolioLoading
from .files import PortfolioFiles
from .menu import PortfolioMenu
from .settings import PortfolioSettings
from .bookmarks import PortfolioBookmarks, PortfolioBookmarkButton
from .trash import default_trash


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/window.ui")
class PortfolioWindow(Adw.ApplicationWindow):
    __gtype_name__ = "PortfolioWindow"

    previous = Gtk.Template.Child()
    next = Gtk.Template.Child()
    search = Gtk.Template.Child()
    rename = Gtk.Template.Child()
    detail = Gtk.Template.Child()
    delete = Gtk.Template.Child()
    cut = Gtk.Template.Child()
    copy = Gtk.Template.Child()
    paste = Gtk.Template.Child()
    select_all = Gtk.Template.Child()
    select_none = Gtk.Template.Child()
    bookmark_box = Gtk.Template.Child()
    new_folder = Gtk.Template.Child()
    delete_trash = Gtk.Template.Child()
    restore_trash = Gtk.Template.Child()
    close_button = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    go_top_button = Gtk.Template.Child()
    about_back_button = Gtk.Template.Child()
    properties_back_button = Gtk.Template.Child()

    search_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    popup_box = Gtk.Template.Child()
    action_stack = Gtk.Template.Child()
    tools_stack = Gtk.Template.Child()
    navigation_box = Gtk.Template.Child()
    selection_box = Gtk.Template.Child()
    selection_tools = Gtk.Template.Child()
    navigation_tools = Gtk.Template.Child()
    places_box = Gtk.Template.Child()
    places_inner_box = Gtk.Template.Child()
    places_popup_box = Gtk.Template.Child()
    content_stack = Gtk.Template.Child()
    loading_box = Gtk.Template.Child()
    loading_inner_box = Gtk.Template.Child()
    content_box = Gtk.Template.Child()
    files_stack = Gtk.Template.Child()
    files_box = Gtk.Template.Child()
    files_title = Gtk.Template.Child()
    about_box = Gtk.Template.Child()
    about_inner_box = Gtk.Template.Child()
    close_box = Gtk.Template.Child()
    close_tools = Gtk.Template.Child()
    stop_box = Gtk.Template.Child()
    stop_tools = Gtk.Template.Child()
    trash_tools = Gtk.Template.Child()
    about_deck = Gtk.Template.Child()
    content_deck = Gtk.Template.Child()
    placeholder_box = Gtk.Template.Child()
    placeholder_inner_box = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    home_menu_button = Gtk.Template.Child()
    content_inner_box = Gtk.Template.Child()
    go_top_revealer = Gtk.Template.Child()
    properties_box = Gtk.Template.Child()
    properties_inner_box = Gtk.Template.Child()
    passphrase_title = Gtk.Template.Child()
    passphrase_box = Gtk.Template.Child()
    passphrase_inner_box = Gtk.Template.Child()
    passphrase_back_button = Gtk.Template.Child()

    SEARCH_DELAY = 500
    LOAD_ANIMATION_DELAY = 250

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()

    def _setup(self):
        self._popup = None
        self._places_popup = None
        self._worker = None
        self._busy = False
        self._to_copy = []
        self._to_cut = []
        self._force_go_home = False
        self._history = []
        self._index = -1
        self._search_delay_handler_id = 0
        self._load_delay_handler_id = 0

        self._settings = PortfolioSettings()
        self._settings.connect("notify::show-hidden", self._on_show_hidden_changed)
        self._settings.connect("notify::sort-order", self._on_sort_order_changed)

        self.previous.connect("clicked", self._on_go_previous)
        self.next.connect("clicked", self._on_go_next)
        self.rename.connect("clicked", self._on_rename_clicked)
        self.detail.connect("clicked", self._on_detail_clicked)
        self.delete.connect("clicked", self._on_delete_clicked)
        self.cut.connect("clicked", self._on_cut_clicked)
        self.copy.connect("clicked", self._on_copy_clicked)
        self.paste.connect("clicked", self._on_paste_clicked)
        self.restore_trash.connect("clicked", self._on_restore_trash_clicked)
        self.delete_trash.connect("clicked", self._on_delete_trash_clicked)
        self.select_all.connect("clicked", self._on_select_all)
        self.select_none.connect("clicked", self._on_select_none)
        self.new_folder.connect("clicked", self._on_new_folder)

        self.close_button.connect("clicked", self._on_button_closed)
        self.go_top_button.connect("clicked", self._go_to_top)
        self.stop_button.connect("clicked", self._on_stop_clicked)
        self.about_back_button.connect("clicked", self._on_about_back_clicked)
        self.properties_back_button.connect("clicked", self._on_properties_back_clicked)
        self.passphrase_back_button.connect("clicked", self._on_passphrase_back_clicked)

        # XXX no model for options yet so this...
        self.menu_popover = PortfolioMenu(self._settings)
        self.menu_popover.connect("show-about", self._on_about_clicked)
        self.menu_button.props.popover = self.menu_popover
        self.menu_button.connect("activate", self._on_menu_button_clicked)

        self.home_menu_popover = PortfolioMenu(self._settings)
        self.home_menu_popover.connect("show-about", self._on_about_clicked)
        self.home_menu_button.props.popover = self.home_menu_popover
        self.home_menu_button.connect("activate", self._on_menu_button_clicked)

        self.search.connect("toggled", self._on_search_toggled)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", self._on_search_stopped)

        # XXX Compose these widgets directly in .ui files
        self.files = PortfolioFiles()
        self.files.connect("activated", self._on_files_activated)
        self.files.connect("selected", self._on_files_selected)
        self.files.connect("rename-started", self._on_files_rename_started)
        self.files.connect("rename-finished", self._on_files_rename_finished)
        self.files.connect("rename-failed", self._on_files_rename_failed)
        self.files.connect("add-failed", self._on_files_add_failed)
        self.files.connect("adjustment-changed", self._on_files_adjustment_changed)
        self.files.sort_order = self._settings.sort_order
        self.content_inner_box.append(self.files)
        self._bookmarks = PortfolioBookmarks()

        self._bookmark_button = PortfolioBookmarkButton(self._bookmarks)
        self.bookmark_box.append(self._bookmark_button)

        places = PortfolioPlaces(self._bookmarks)
        places.connect("updated", self._on_places_updated)
        places.connect("removing", self._on_places_removing)
        places.connect("removed", self._on_places_removed)
        places.connect("failed", self._on_places_failed)
        places.connect("unlock", self._on_places_unlock)
        self.places_inner_box.append(places)

        self._properties_worker = PortfolioPropertiesWorker()
        self.properties_inner_box.append(PortfolioProperties(self._properties_worker))

        self.about_inner_box.append(PortfolioAbout())

        self.passphrase = PortfolioPassphrase()
        self.passphrase.connect("unlocked", self._on_places_unlocked)
        self.passphrase_inner_box.append(self.passphrase)

        self.placeholder_inner_box.append(PortfolioPlaceholder())

        self.loading = PortfolioLoading()
        self.loading_inner_box.append(self.loading)

        self.content_deck.connect("notify::visible-child", self._on_content_folded)
        self.connect("close-request", self._on_close_request)

    def _populate(self, directory):
        self.files.switch_to_navigation_mode()

        if self._worker is not None:
            self._worker.stop()

        if default_trash.is_trash(directory):
            loader_class = PortfolioLoadTrashWorker
        else:
            loader_class = PortfolioLoadWorker

        self._worker = loader_class(directory, self._settings.show_hidden)
        self._worker.connect("started", self._on_load_started)
        self._worker.connect("updated", self._on_load_updated)
        self._worker.connect("finished", self._on_load_finished)
        self._worker.connect("failed", self._on_load_failed)
        self._worker.start()
        self._bookmark_button.path = directory


    def _paste(self, Worker, to_paste):
        directory = self._history[self._index]

        self._worker = Worker(to_paste, directory)
        self._worker.connect("started", self._on_paste_started)
        self._worker.connect("updated", self._on_paste_updated)
        self._worker.connect("post-update", self._on_paste_post_updated)
        self._worker.connect("finished", self._on_paste_finished)
        self._worker.connect("failed", self._on_paste_failed)
        self._worker.connect("stopped", self._on_paste_stopped)
        self._worker.start()

    def _paste_finish(self):
        self._busy = False
        self._clean_workers()
        self.loading.clean()

        self._to_cut = []
        self._to_copy = []

        self.files.unselect_all()
        self._update_all()

    def _delete_finish(self):
        self._busy = False
        self._clean_workers()
        self.loading.clean()

        self.files.unselect_all()
        self._update_all()

    def _get_row(self, model, treepath):
        return model.get_iter(treepath)

    def _go_to_top(self, *args):
        self.files.go_to_top()

    def _go_back_to_homepage(self):
        self.content_deck.set_visible_child(self.places_box)

    def _go_to_files_view(self, duration):
        self.content_deck.set_visible_child(self.files_stack)
        self.files_stack.props.transition_duration = duration
        self.files_stack.set_visible_child(self.files_box)

    def _move(self, path, navigating=False):
        self._clean_popups()

        if path is None:
            return
        elif default_trash.is_trash(path) or utils.is_file_dir(path):
            self._update_history(path, navigating)
            self._populate(path)
        else:
            self._open(path)

    def _open(self, path):
        self._worker = PortfolioOpenWorker(path)
        self._worker.connect("started", self._on_open_started)
        self._worker.connect("updated", self._on_open_updated)
        self._worker.connect("finished", self._on_open_finished)
        self._worker.connect("failed", self._on_open_failed)
        self._worker.start()

    def _reset_to_path(self, path):
        self._history = []
        self._index = -1
        self._move(path, False)

    def _refresh(self):
        if self._index > -1:
            self._move(self._history[self._index], True)

    def _notify(self, description, on_confirm, on_cancel, on_trash, autoclose, data):
        self._clean_popups()

        self._popup = PortfolioPopup(
            description, on_confirm, on_cancel, on_trash, autoclose, data
        )
        self.popup_box.append(self._popup)
        self._popup.props.reveal_child = True

    def _places_notify(self, description):
        self._clean_places_popups()

        self._places_popup = PortfolioPopup(description, None, None, None, False, None)
        self.places_popup_box.append(self._places_popup)
        self._places_popup.props.reveal_child = True

    def _clean_workers(self):
        del self._worker
        self._worker = None

    def _clean_popups(self):
        if self._popup is None:
            return
        if self._popup.get_parent() is not None:
            self.popup_box.remove(self._popup)
        self._popup = None

    def _clean_places_popups(self):
        if self._places_popup is None:
            return
        if self._places_popup.get_parent() is not None:
            self.places_popup_box.remove(self._places_popup)
        self._places_popup = None

    def _clean_loading_delay(self):
        if self._load_delay_handler_id != 0:
            GLib.Source.remove(self._load_delay_handler_id)
            self._load_delay_handler_id = 0

    def _update_history(self, path, navigating):
        if path not in self._history or not navigating:
            del self._history[self._index + 1 :]
            self._history.append(path)
            self._index += 1

    def _update_all(self):
        self._update_search()
        self._update_treeview()
        self._update_content_stack()
        self._update_navigation()
        self._update_navigation_tools()
        self._update_trash_tools()
        self._update_selection()
        self._update_selection_tools()
        self._update_action_stack()
        self._update_tools_stack()
        self._update_menu()

    def _update_search(self):
        sensitive = not self.files.is_editing and not self._busy
        self.search.props.sensitive = sensitive
        self.search_entry.sensitive = sensitive

    def _update_treeview(self):
        self.files.update(not self._busy)

    def _update_content_stack(self):
        if self._busy:
            return
        elif self.files.is_empty:
            self.content_stack.set_visible_child(self.placeholder_box)
        else:
            self.content_stack.set_visible_child(self.content_box)

    def _update_navigation(self):
        count = self.files.selected_count
        selected = count >= 1

        if selected or self._busy:
            self.previous.props.sensitive = False
            self.next.props.sensitive = False
            return

        self.previous.props.sensitive = True
        self.next.props.sensitive = (
            True if len(self._history) - 1 > self._index else False
        )

    def _update_selection(self):
        sensitive = not self.files.is_editing and not self._busy

        self.select_all.props.sensitive = sensitive
        self.select_none.props.sensitive = sensitive

    def _update_action_stack(self):
        count = self.files.selected_count
        selected = count >= 1
        child = self.selection_box if selected else self.navigation_box
        self.action_stack.set_visible_child(child)

    def _update_tools_stack(self):
        directory = self._history[self._index]
        if default_trash.in_trash(directory):
            self.tools_stack.set_visible_child(self.trash_tools)
            return

        count = self.files.selected_count
        selected = count >= 1
        child = self.selection_tools if selected else self.navigation_tools
        self.tools_stack.set_visible_child(child)

    def _update_selection_tools(self):
        count = self.files.selected_count
        sensitive = count >= 1 and not self.files.is_editing and not self._busy

        self.delete.props.sensitive = sensitive
        self.cut.props.sensitive = sensitive
        self.copy.props.sensitive = sensitive

        self._update_rename()
        self._update_detail()

    def _update_navigation_tools(self):
        count = self.files.selected_count
        selected = count >= 1
        to_paste = len(self._to_cut) >= 1 or len(self._to_copy) >= 1
        self.paste.props.sensitive = not selected and to_paste and not self._busy
        self.new_folder.props.sensitive = not selected and not self._busy

    def _update_trash_tools(self):
        selected = self.files.selected_count >= 1
        is_trash = default_trash.is_trash(self._history[self._index])
        self.restore_trash.props.sensitive = selected and is_trash
        self.delete_trash.props.sensitive = selected and is_trash

    def _update_rename(self):
        count = self.files.selected_count
        sensitive = count == 1 and not self.files.is_editing and not self._busy
        self.rename.props.sensitive = sensitive

    def _update_detail(self):
        count = self.files.selected_count
        sensitive = count == 1 and not self.files.is_editing and not self._busy
        self.detail.props.sensitive = sensitive

    def _update_directory_title(self):
        directory = self._history[self._index]

        if default_trash.is_trash(directory):
            name = PortfolioPlaces.XDG_TRASH_NAME
        else:
            name = os.path.basename(directory)

        self.files_title.props.title = name

    def _update_filter(self):
        self.files.filter = self.search_entry.get_text()
        self._update_content_stack()

        self._search_delay_handler_id = 0
        return GLib.SOURCE_REMOVE

    def _update_menu(self):
        self.menu_popover.is_sensitive = not self._busy
        self.home_menu_popover.is_sensitive = not self._busy

    def _reset_search(self):
        self.search.set_active(False)
        self.search_entry.set_text("")
        self.search.grab_focus()

    def _on_files_activated(self, files, path):
        self._move(path)

    def _on_files_selected(self, files):
        if self._busy is True:
            return
        self._update_all()

    def _on_files_rename_started(self, files):
        self._update_search()
        self._update_selection()
        self._update_selection_tools()

    def _on_files_rename_finished(self, files):
        self._update_all()

    def _on_files_rename_failed(self, files, new_name):
        self._on_rename_clicked(None)
        self._notify(
            _("%s already exists") % new_name,
            None,
            self._on_popup_closed,
            None,
            True,
            None,
        )

    def _on_files_add_failed(self, files):
        self._notify(
            _("No permissions on this directory"),
            None,
            self._on_popup_closed,
            None,
            True,
            None,
        )

    def _on_files_adjustment_changed(self, files, reveal):
        self.go_top_revealer.props.reveal_child = reveal

    def _on_open_started(self, worker):
        self._busy = True
        self.loading.update(_("Opening"), 0.0, "", "")
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_open_updated(self, worker):
        self.loading.pulse()

    def _on_open_finished(self, worker):
        self._busy = False
        self._clean_workers()
        self._update_all()

    def _on_open_failed(self, worker, path):
        self._busy = False
        self._clean_workers()

        name = os.path.basename(path)
        self.loading.update(description=_("Could not open %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_load_started(self, worker, directory):
        self._busy = True

        self.files.clear()
        self._update_directory_title()
        self._reset_search()
        self._update_all()

        self._load_delay_handler_id = GLib.timeout_add(
            self.LOAD_ANIMATION_DELAY,
            self._on_load_started_delayed,
        )

    def _on_load_started_delayed(self):
        self.loading.update(_("Loading"), 0.0, "", "")
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self._load_delay_handler_id = 0
        return GLib.SOURCE_REMOVE

    def _on_load_updated(self, worker, directory, found, index, total):
        for name, path, icon in found:
            self.files.add_row(icon, name, path)

        self.loading.update(progress=(index + 1) / total)

    def _on_load_finished(self, worker, directory):
        self._busy = False
        self._clean_workers()
        self._clean_loading_delay()

        self._update_all()
        self.files.update_scrolling()

    def _on_load_failed(self, worker, directory):
        self._busy = False
        self._clean_workers()
        self._clean_loading_delay()

        name = os.path.basename(directory)
        self.loading.update(
            title=_("Loading"), description=_("Could not load %s") % name
        )
        self.content_stack.set_visible_child(self.loading_box)

        self.files._clear_select_and_go()
        self._force_go_home = True
        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_go_previous(self, button):
        if self._index == 0:
            self._go_back_to_homepage()
        else:
            self.files.to_go_to_path = self._history[self._index]
            self._index -= 1
            self._move(self._history[self._index], True)

    def _on_go_next(self, button):
        self._index += 1
        self._move(self._history[self._index], True)

    def _on_search_toggled(self, button):
        toggled = self.search.get_active()
        self.search_box.props.search_mode_enabled = toggled

    def _on_search_changed(self, entry):
        if self._search_delay_handler_id != 0:
            GLib.Source.remove(self._search_delay_handler_id)
        self._search_delay_handler_id = GLib.timeout_add(
            self.SEARCH_DELAY, self._update_filter
        )

    def _on_search_stopped(self, entry):
        self._reset_search()

    def _on_detail_clicked(self, button):
        path = self.files.get_selected_path()
        self.show_properties(path)

    def _on_rename_clicked(self, button):
        self.files.rename_selected_row()

    def _on_delete_clicked(self, button):
        selection = self.files.get_selection()
        count = len(selection)
        directory = self._history[self._index]

        if count == 1:
            name = os.path.basename(selection[0][0])
        else:
            name = _("these %d files") % count

        description = _("Delete %s permanently?") % name

        self._notify(
            description,
            self._on_delete_confirmed,
            self._on_popup_closed,
            self._on_trash_instead if default_trash.has_trash(directory) else None,
            False,
            selection,
        )

    def _on_cut_clicked(self, button):
        selection = self.files.get_selection()
        count = len(selection)

        self._to_cut = selection
        self._to_copy = []

        if count == 1:
            name = os.path.basename(selection[0][0])
            description = _("%s will be moved") % name
        else:
            description = _("%d files will be moved") % count

        self._notify(description, None, None, None, True, None)

        self.files.unselect_all()

    def _on_copy_clicked(self, button):
        selection = self.files.get_selection()
        count = len(selection)

        self._to_copy = selection
        self._to_cut = []

        if count == 1:
            name = os.path.basename(selection[0][0])
            description = _("%s will be copied") % name
        else:
            description = _("%d files will be copied") % count

        self._notify(description, None, None, None, True, None)

        self.files.unselect_all()

    def _on_paste_clicked(self, button):
        to_paste = self._to_copy if self._to_copy else self._to_cut
        Worker = PortfolioCopyWorker if self._to_copy else PortfolioCutWorker

        directory = self._history[self._index]
        should_warn = any(
            [
                os.path.dirname(path) != directory
                and os.path.lexists(os.path.join(directory, os.path.basename(path)))
                for path, ref in to_paste
            ]
        )

        if not should_warn:
            self._paste(Worker, to_paste)
            return

        self._notify(
            _("Files will be overwritten, proceed?"),
            self._on_paste_confirmed,
            self._on_popup_closed,
            None,
            False,
            (to_paste, Worker),
        )

    def _on_paste_confirmed(self, button, popup, data):
        to_paste, Worker = data
        self._clean_popups()
        self._paste(Worker, to_paste)

    def _on_paste_started(self, worker, total):
        self._busy = True
        self.loading.update(_("Pasting"), 0.0, "", "")
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self.action_stack.set_visible_child(self.stop_box)
        self.tools_stack.set_visible_child(self.stop_tools)

    def _on_paste_post_updated(self, worker, name, path, icon, overwritten):
        if overwritten:
            return
        if not os.path.exists(path):
            logger.debug(f"Attempting to add unexisting {path}")
            return

        self.files.add_row(icon, name, path)

    def _on_paste_updated(self, worker, path, index, total, current_bytes, total_bytes):
        description = os.path.basename(path)
        human_current_bytes = utils.get_size_for_humans(current_bytes)
        human_total_bytes = utils.get_size_for_humans(total_bytes)
        self.loading.update(
            description=description,
            progress=index / total,
            details=_("%s of %s") % (human_current_bytes, human_total_bytes),
        )

    def _on_paste_finished(self, worker, total):
        self._paste_finish()

    def _on_paste_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self.loading.clean()

        self._to_cut = []
        self._to_copy = []

        name = os.path.basename(path)
        self.loading.update(description=_("Could not paste %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_paste_stopped(self, worker):
        self._paste_finish()
        # XXX nuclear fix for when parent directory does not get to be updated
        self._refresh()

    def _on_trash_instead(self, button, popup, selection):
        self._clean_popups()

        # clean history entries from deleted paths
        directory = self._history[self._index]
        self._history = [
            path
            for path in self._history
            if not path.startswith(directory) or path == directory
        ]

        self._worker = PortfolioSendTrashWorker(selection)
        self._worker.connect("started", self._on_delete_started)
        self._worker.connect("pre-update", self._on_delete_pre_updated)
        self._worker.connect("updated", self._on_delete_updated)
        self._worker.connect("finished", self._on_delete_finished)
        self._worker.connect("failed", self._on_delete_failed)
        self._worker.connect("stopped", self._on_delete_stopped)
        self._worker.start()

    def _on_delete_confirmed(self, button, popup, selection):
        self._clean_popups()

        # clean history entries from deleted paths
        directory = self._history[self._index]
        self._history = [
            path
            for path in self._history
            if not path.startswith(directory) or path == directory
        ]

        self._worker = PortfolioDeleteWorker(selection)
        self._worker.connect("started", self._on_delete_started)
        self._worker.connect("pre-update", self._on_delete_pre_updated)
        self._worker.connect("updated", self._on_delete_updated)
        self._worker.connect("finished", self._on_delete_finished)
        self._worker.connect("failed", self._on_delete_failed)
        self._worker.connect("stopped", self._on_delete_stopped)
        self._worker.start()

    def _on_delete_started(self, worker):
        self._busy = True
        self.loading.update(_("Deleting"), 0.0, "", "")
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self.action_stack.set_visible_child(self.stop_box)
        self.tools_stack.set_visible_child(self.stop_tools)

    def _on_delete_pre_updated(self, worker, path):
        name = os.path.basename(path)
        self.loading.update(description=name)

    def _on_delete_updated(self, worker, path, row, index, total):
        self.files.remove_row(row)
        self.loading.update(progress=(index + 1) / total)

    def _on_delete_finished(self, worker, total):
        self._delete_finish()

    def _on_delete_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self.loading.clean()

        name = os.path.basename(path)
        self.loading.update(description=_("Could not delete %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_delete_stopped(self, worker):
        self._delete_finish()

    def _on_popup_closed(self, button, popup, data):
        self._clean_popups()

    def _on_button_closed(self, button):
        self.loading.clean()
        self.files.unselect_all()
        self._update_all()

        if self._force_go_home is False:
            return

        self._force_go_home = False
        self._go_back_to_homepage()

    def _on_stop_clicked(self, button):
        self.loading.update(title=_("Stopping"))
        self._worker.stop()

    def _on_select_all(self, button):
        self.files.select_all()

    def _on_select_none(self, button):
        self.files.unselect_all()

    def _on_new_folder(self, button):
        directory = self._history[self._index]
        self.files.add_new_folder_row(directory)

    def _on_restore_trash_clicked(self, button):
        selection = self.files.get_selection()
        paths = [default_trash.get_orig_path(path) for path, ref in selection]

        overwrites = any([os.path.lexists(path) for path in paths if path])
        duplicates = len(set(paths)) != len(paths)

        if not overwrites and not duplicates:
            self._on_restore_trash_confirmed(None, None, selection)
            return

        self._notify(
            _("Files will be overwritten, proceed?"),
            self._on_restore_trash_confirmed,
            self._on_popup_closed,
            None,
            False,
            selection,
        )

    def _on_restore_trash_confirmed(self, button, popup, selection):
        self._clean_popups()

        self._worker = PortfolioRestoreTrashWorker(selection)
        self._worker.connect("started", self._on_restore_trash_started)
        self._worker.connect("pre-update", self._on_restore_trash_pre_updated)
        self._worker.connect("updated", self._on_restore_trash_updated)
        self._worker.connect("finished", self._on_restore_trash_finished)
        self._worker.connect("failed", self._on_restore_trash_failed)
        self._worker.connect("stopped", self._on_restore_trash_stopped)
        self._worker.start()

    def _on_restore_trash_started(self, worker):
        self._busy = True

        self.loading.update(_("Restoring"), 0.0, "", "")
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self.action_stack.set_visible_child(self.stop_box)
        self.tools_stack.set_visible_child(self.stop_tools)

    def _on_restore_trash_pre_updated(self, worker, path):
        name = os.path.basename(path)
        self.loading.update(description=name)

    def _on_restore_trash_updated(self, worker, path, row, index, total):
        self.files.remove_row(row)
        self.loading.update(progress=(index + 1) / total)

    def _on_restore_trash_finished(self, worker, total):
        self._busy = False
        self._clean_workers()
        self.loading.clean()

        self.files.unselect_all()
        self._update_all()

    def _on_restore_trash_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self.loading.clean()

        self.loading.update(description=_("Could not restore %s") % path)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_restore_trash_stopped(self, worker):
        self._delete_finish()

    def _on_delete_trash_clicked(self, button):
        selection = self.files.get_selection()
        count = len(selection)

        if count == 1:
            name = os.path.basename(selection[0][0])
        else:
            name = _("these %d files") % count

        description = _("Delete %s permanently?") % name

        self._notify(
            description,
            self._on_delete_trash_confirmed,
            self._on_popup_closed,
            None,
            False,
            selection,
        )

    def _on_delete_trash_confirmed(self, button, popup, selection):
        self._clean_popups()

        self._worker = PortfolioDeleteTrashWorker(selection)
        self._worker.connect("started", self._on_delete_trash_started)
        self._worker.connect("pre-update", self._on_delete_trash_pre_updated)
        self._worker.connect("updated", self._on_delete_trash_updated)
        self._worker.connect("finished", self._on_delete_trash_finished)
        self._worker.connect("failed", self._on_delete_trash_failed)
        self._worker.connect("stopped", self._on_delete_trash_stopped)
        self._worker.start()

    def _on_delete_trash_started(self, worker):
        self._busy = True

        self.loading.update(_("Deleting"), 0.0, "", "")
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self.action_stack.set_visible_child(self.stop_box)
        self.tools_stack.set_visible_child(self.stop_tools)

    def _on_delete_trash_pre_updated(self, worker, path):
        name = os.path.basename(path)
        self.loading.update(description=name)

    def _on_delete_trash_updated(self, worker, path, row, index, total):
        self.files.remove_row(row)
        self.loading.update(progress=(index + 1) / total)

    def _on_delete_trash_finished(self, worker, total):
        self._delete_finish()

    def _on_delete_trash_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self.loading.clean()

        self.loading.update(description=_("Could not delete %s") % path)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_delete_trash_stopped(self, worker):
        self._delete_finish()

    def _on_places_updated(self, button, path):
        self._reset_to_path(path)
        self._go_to_files_view(duration=0)

    def _on_places_removing(self, button, path):
        self._places_notify(_("Removing device, please wait"))

    def _on_places_removed(self, button, path, safely):
        if safely is True:
            self._places_notify(_("Device can be removed"))

        if self._index == -1:
            return

        directory = self._history[self._index]
        if not path or not directory.startswith(path):
            return

        self._go_back_to_homepage()

    def _on_places_failed(self, button, path):
        self._places_notify(_("Device is busy, can't be removed"))

    def _on_places_unlock(self, button, encrypted):
        self.passphrase.unlock(encrypted)
        self.passphrase_title.props.title = encrypted.get_friendly_label()
        self.content_deck.set_visible_child(self.files_stack)
        self.files_stack.set_visible_child(self.passphrase_box)

    def _on_places_unlocked(self, widget, path):
        self._reset_to_path(path)
        self._go_to_files_view(duration=200)

    def _on_passphrase_back_clicked(self, button):
        self.passphrase.clean()
        self.content_deck.set_visible_child(self.places_box)

    def _on_about_clicked(self, button):
        self.about_deck.set_visible_child(self.about_box)

    def _on_about_back_clicked(self, button):
        self.about_deck.set_visible_child(self.content_deck)

    def _on_properties_back_clicked(self, button):
        self.content_deck.set_visible_child(self.files_stack)

    def _on_show_hidden_changed(self, settings, data):
        self._refresh()

    def _on_sort_order_changed(self, settings, data):
        self.files.sort_order = self._settings.sort_order
        self._refresh()

    def _on_menu_button_clicked(self, button):
        button.props.popover.popup()

    def _on_content_folded(self, deck, data=None):
        child = self.content_deck.get_visible_child()
        if child == self.places_box and self._worker is not None:
            self._worker.stop()
            self._clean_workers()
        elif child == self.files_box:
            self._properties_worker.stop()

    def _on_close_request(self, window):
        if self._worker is not None:
            self._worker.stop()
        self._properties_worker.stop()

    def open(self, path=PortfolioPlaces.PORTFOLIO_HOME_DIR, force_page_switch=False):
        path = utils.get_uri_path(path)

        # make sure it exists though !
        if not os.path.exists(path):
            logger.warning(_("Could not open %s") % path)
            return

        # if it's a file then use its parent folder
        if not os.path.isdir(path):
            self.files.to_select_path = path
            path = os.path.dirname(path)

        # XXX no support for background workers yet
        if self._busy and not isinstance(self._worker, PortfolioLoadWorker):
            logger.warning(_("Could not open %s") % path)
            return

        if isinstance(self._worker, PortfolioLoadWorker):
            self._worker.stop()
            self._clean_workers()
            self._clean_loading_delay()

        self._reset_to_path(path)

        if force_page_switch is False:
            return

        self.about_deck.set_visible_child(self.content_deck)
        self.content_deck.set_visible_child(self.files_stack)

    def show_properties(self, path, force_page_switch=False):
        self._properties_worker.props.path = path

        if force_page_switch is True:
            self.open(path, force_page_switch)

        self.content_deck.set_visible_child(self.properties_box)
