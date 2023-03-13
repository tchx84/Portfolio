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

from pathlib import Path

from .translation import gettext as _

from gi.repository import Gtk, GLib, Gio, Handy, GObject

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
from .settings import PortfolioSettings
from .trash import default_trash


@Gtk.Template(resource_path="/dev/tchx84/Portfolio/window.ui")
class PortfolioWindow(Handy.ApplicationWindow):
    __gtype_name__ = "PortfolioWindow"

    name_column = Gtk.Template.Child()
    name_cell = Gtk.Template.Child()
    sorted = Gtk.Template.Child()
    filtered = Gtk.Template.Child()
    selection = Gtk.Template.Child()
    liststore = Gtk.Template.Child()
    treeview = Gtk.Template.Child()
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
    new_folder = Gtk.Template.Child()
    delete_trash = Gtk.Template.Child()
    restore_trash = Gtk.Template.Child()
    loading_label = Gtk.Template.Child()
    loading_bar = Gtk.Template.Child()
    loading_description = Gtk.Template.Child()
    loading_details = Gtk.Template.Child()
    close_button = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    help_button = Gtk.Template.Child()
    about_button = Gtk.Template.Child()
    show_hidden_button = Gtk.Template.Child()
    a_to_z_button = Gtk.Template.Child()
    last_modified_button = Gtk.Template.Child()
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
    content_box = Gtk.Template.Child()
    files_stack = Gtk.Template.Child()
    files_box = Gtk.Template.Child()
    about_box = Gtk.Template.Child()
    close_box = Gtk.Template.Child()
    close_tools = Gtk.Template.Child()
    stop_box = Gtk.Template.Child()
    stop_tools = Gtk.Template.Child()
    trash_tools = Gtk.Template.Child()
    about_deck = Gtk.Template.Child()
    content_deck = Gtk.Template.Child()
    headerbar = Gtk.Template.Child()
    placeholder_box = Gtk.Template.Child()
    menu_box = Gtk.Template.Child()
    menu_popover = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    home_menu_button = Gtk.Template.Child()
    content_scroll = Gtk.Template.Child()
    go_top_revealer = Gtk.Template.Child()
    properties_box = Gtk.Template.Child()
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
    passphrase_header = Gtk.Template.Child()
    passphrase_box = Gtk.Template.Child()
    passphrase_entry = Gtk.Template.Child()
    passphrase_label = Gtk.Template.Child()
    passphrase_spinner = Gtk.Template.Child()
    passphrase_back_button = Gtk.Template.Child()

    ICON_COLUMN = 0
    NAME_COLUMN = 1
    PATH_COLUMN = 2
    SEARCH_DELAY = 500
    LOAD_ANIMATION_DELAY = 250

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup()
        self._setup_settings()

    def _setup(self):
        Handy.init()
        Handy.StyleManager.get_default().set_color_scheme(
            Handy.ColorScheme.PREFER_LIGHT
        )

        self._popup = None
        self._places_popup = None
        self._worker = None
        self._busy = False
        self._editing = False
        self._to_copy = []
        self._to_cut = []
        self._to_select = None
        self._to_select_row = None
        self._to_go_to = None
        self._to_go_to_row = None
        self._last_clicked = None
        self._last_vscroll_value = None
        self._dont_activate = False
        self._force_select = False
        self._force_go_home = False
        self._history = []
        self._index = -1
        self._search_delay_handler_id = 0
        self._load_delay_handler_id = 0
        self._encrypted = None

        self.gesture = Gtk.GestureLongPress.new(self.treeview)
        self.gesture.connect("pressed", self._on_long_pressed)

        self.filtered.set_visible_func(self._filter, data=None)
        self.sorted.set_default_sort_func(self._sort, None)
        self.selection.connect("changed", self._on_selection_changed)
        self.selection.set_select_function(self._on_select)
        self.treeview.connect("row-activated", self._on_row_activated)
        self.treeview.connect("button-press-event", self._on_clicked)

        self.name_cell.connect("editing-started", self._on_rename_started)
        self.name_cell.connect("editing-canceled", self._on_rename_finished)
        self.name_cell.connect("edited", self._on_rename_updated)

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
        self.help_button.connect("clicked", self._on_help_clicked)
        self.about_button.connect("clicked", self._on_about_clicked)
        self.show_hidden_button.connect("toggled", self._on_hidden_toggled)
        self.a_to_z_button.connect("toggled", self._on_sort_toggled)
        self.go_top_button.connect("clicked", self._go_to_top)
        self.stop_button.connect("clicked", self._on_stop_clicked)
        self.about_back_button.connect("clicked", self._on_about_back_clicked)
        self.properties_back_button.connect("clicked", self._on_properties_back_clicked)
        self.passphrase_back_button.connect("clicked", self._on_passphrase_back_clicked)
        self.passphrase_entry.connect("activate", self._on_passphrase_activate)

        # XXX no model for options yet so this...
        self.menu_button.connect("clicked", self._on_menu_button_clicked)
        self.home_menu_button.connect("clicked", self._on_menu_button_clicked)

        self._adjustment = self.content_scroll.get_vadjustment()
        self._adjustment.connect("value-changed", self._update_go_top_button)

        self.search.connect("toggled", self._on_search_toggled)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", self._on_search_stopped)

        places = PortfolioPlaces()
        places.connect("updated", self._on_places_updated)
        places.connect("removing", self._on_places_removing)
        places.connect("removed", self._on_places_removed)
        places.connect("failed", self._on_places_failed)
        places.connect("unlock", self._on_places_unlock)
        self.places_inner_box.add(places)

        self._properties = PortfolioPropertiesWorker()
        self._properties.bind_property(
            "name",
            self.property_name,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "location",
            self.property_location,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "type",
            self.property_type,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "size",
            self.property_size,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "created",
            self.property_created,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "modified",
            self.property_modified,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "accessed",
            self.property_accessed,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "permissions_owner",
            self.property_permissions_owner,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "permissions_group",
            self.property_permissions_group,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "permissions_others",
            self.property_permissions_others,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "owner",
            self.property_owner,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._properties.bind_property(
            "group",
            self.property_group,
            "label",
            GObject.BindingFlags.SYNC_CREATE,
        )

        self.content_deck.connect("notify::visible-child", self._on_content_folded)
        self.connect("destroy", self._on_shutdown)

    def _setup_settings(self):
        self._settings = PortfolioSettings()

        self.show_hidden_button.props.active = self._settings.show_hidden

        if self._settings.sort_order == PortfolioSettings.ALPHABETICAL_ORDER:
            self.a_to_z_button.props.active = True
        else:
            self.last_modified_button.props.active = True

    def _filter(self, model, row, data=None):
        path = model[row][self.PATH_COLUMN]
        text = self.search_entry.get_text()
        if not text:
            return True
        return text.lower() in os.path.basename(path).lower()

    def _sort_by_last_modified(self, path1, path2):
        st_mtime1 = utils.get_file_mtime(path1)
        st_mtime2 = utils.get_file_mtime(path2)

        if st_mtime1 < st_mtime2:
            return 1
        elif st_mtime1 > st_mtime2:
            return -1

        return 0

    def _sort_by_a_to_z(self, path1, path2):
        path1 = path1.lower()
        path2 = path2.lower()

        if path1 < path2:
            return -1
        elif path1 > path2:
            return 1

        return 0

    def _sort(self, model, row1, row2, data=None):
        path1 = model[row1][self.PATH_COLUMN]
        path2 = model[row2][self.PATH_COLUMN]

        row1_is_dir = utils.is_file_dir(path1)
        row2_is_dir = utils.is_file_dir(path2)

        if row1_is_dir and not row2_is_dir:
            return -1
        elif not row1_is_dir and row2_is_dir:
            return 1

        if self.a_to_z_button.props.active:
            return self._sort_by_a_to_z(path1, path2)
        else:
            return self._sort_by_last_modified(path1, path2)

    def _select_all(self):
        self._force_select = True
        self.selection.select_all()
        self._force_select = False

    def _unselect_all(self):
        self._force_select = True
        self.selection.unselect_all()
        self._force_select = False

    def _select_row(self, row):
        self._force_select = True
        self.selection.select_iter(row)
        self._force_select = False

    def _select_and_go(self, row, edit=False):
        result, row = self.filtered.convert_child_iter_to_iter(row)
        result, row = self.sorted.convert_child_iter_to_iter(row)

        self._select_row(row)
        GLib.idle_add(self._go_to_selection)

        if edit is True:
            GLib.timeout_add(100, self._wait_and_edit)

    def _wait_and_edit(self):
        value = self._adjustment.get_value()

        if value == self._last_vscroll_value:
            self._on_rename_clicked(None)
            self._last_vscroll_value = None
            return False

        self._last_vscroll_value = value
        return True

    def _get_selection(self):
        model, treepaths = self.selection.get_selected_rows()
        selection = [
            (
                model[treepath][self.PATH_COLUMN],
                Gtk.TreeRowReference.new(model, treepath),
            )
            for treepath in treepaths
        ]
        return selection

    def _remove_row(self, ref):
        if ref is None or not ref.valid():
            return

        treepath = ref.get_path()
        treepath = self.sorted.convert_path_to_child_path(treepath)
        treepath = self.filtered.convert_path_to_child_path(treepath)

        self.liststore.remove(self.liststore.get_iter(treepath))

    def _populate(self, directory):
        self._switch_to_navigation_mode()

        if self._worker is not None:
            self._worker.stop()

        if default_trash.is_trash(directory):
            loader_class = PortfolioLoadTrashWorker
        else:
            loader_class = PortfolioLoadWorker

        self._worker = loader_class(directory, self.show_hidden_button.props.active)
        self._worker.connect("started", self._on_load_started)
        self._worker.connect("updated", self._on_load_updated)
        self._worker.connect("finished", self._on_load_finished)
        self._worker.connect("failed", self._on_load_failed)
        self._worker.start()

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
        self._clean_progress()

        self._to_cut = []
        self._to_copy = []

        self._unselect_all()

        self._update_all()
        self._update_mode()

    def _delete_finish(self):
        self._busy = False
        self._clean_workers()
        self._clean_progress()

        self._unselect_all()
        self._update_all()
        self._update_mode()

    def _get_row(self, model, treepath):
        return model.get_iter(treepath)

    def _get_path(self, model, treepath):
        return model[model.get_iter(treepath)][self.PATH_COLUMN]

    def _go_to(self, row):
        result, row = self.filtered.convert_child_iter_to_iter(row)
        result, row = self.sorted.convert_child_iter_to_iter(row)

        treepath = self.sorted.get_path(row)

        self.treeview.scroll_to_cell(treepath, None, False, 0, 0)

    def _go_to_selection(self):
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        self.treeview.set_cursor_on_cell(
            treepath, self.name_column, self.name_cell, False
        )
        self.treeview.scroll_to_cell(treepath, None, False, 0, 0)

    def _go_to_top(self, *args):
        if len(self.sorted) >= 1:
            self.treeview.scroll_to_cell(0, None, True, 0, 0)

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
        self._update_mode()

    def _refresh(self):
        if self._index > -1:
            self._move(self._history[self._index], True)

    def _switch_to_navigation_mode(self):
        self.selection.set_mode(Gtk.SelectionMode.NONE)

    def _switch_to_selection_mode(self):
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)

    def _notify(self, description, on_confirm, on_cancel, on_trash, autoclose, data):
        self._clean_popups()

        self._popup = PortfolioPopup(
            description, on_confirm, on_cancel, on_trash, autoclose, data
        )
        self.popup_box.add(self._popup)
        self._popup.props.reveal_child = True

    def _places_notify(self, description):
        if self._places_popup is not None:
            self._places_popup.destroy()

        self._places_popup = PortfolioPopup(description, None, None, None, False, None)
        self.places_popup_box.add(self._places_popup)
        self._places_popup.props.reveal_child = True

    def _clean_workers(self):
        del self._worker
        self._worker = None

    def _clean_popups(self):
        if self._popup is None:
            return
        self._popup.destroy()
        self._popup = None

    def _clean_progress(self):
        self.loading_description.set_text("")
        self.loading_details.set_text("")
        self.loading_details.props.visible = False

    def _clean_loading_delay(self):
        if self._load_delay_handler_id != 0:
            GLib.Source.remove(self._load_delay_handler_id)
            self._load_delay_handler_id = 0

    def _clean_passphrase(self):
        self._encrypted = None
        self.passphrase_entry.set_text("")
        self.passphrase_label.set_text("")
        self.passphrase_entry.props.sensitive = True
        self.passphrase_label.props.visible = True
        self.passphrase_spinner.props.visible = False
        self.passphrase_spinner.props.active = False

    def _update_mode(self):
        count = self.selection.count_selected_rows()
        if count == 0:
            self._switch_to_navigation_mode()

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
        self._update_go_top_button()

    def _update_search(self):
        sensitive = not self._editing and not self._busy
        self.search.props.sensitive = sensitive
        self.search_entry.sensitive = sensitive

    def _update_treeview(self):
        sensitive = not self._busy
        self.treeview.props.sensitive = sensitive

    def _update_content_stack(self):
        if self._busy:
            return
        elif len(self.sorted) == 0:
            self.content_stack.set_visible_child(self.placeholder_box)
        else:
            self.content_stack.set_visible_child(self.content_box)

    def _update_navigation(self):
        count = self.selection.count_selected_rows()
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
        sensitive = not self._editing and not self._busy

        self.select_all.props.sensitive = sensitive
        self.select_none.props.sensitive = sensitive

    def _update_action_stack(self):
        count = self.selection.count_selected_rows()
        selected = count >= 1
        child = self.selection_box if selected else self.navigation_box
        self.action_stack.set_visible_child(child)

    def _update_tools_stack(self):
        directory = self._history[self._index]
        if default_trash.in_trash(directory):
            self.tools_stack.set_visible_child(self.trash_tools)
            return

        count = self.selection.count_selected_rows()
        selected = count >= 1
        child = self.selection_tools if selected else self.navigation_tools
        self.tools_stack.set_visible_child(child)

    def _update_selection_tools(self):
        count = self.selection.count_selected_rows()
        sensitive = count >= 1 and not self._editing and not self._busy

        self.delete.props.sensitive = sensitive
        self.cut.props.sensitive = sensitive
        self.copy.props.sensitive = sensitive

        self._update_rename()
        self._update_detail()

    def _update_navigation_tools(self):
        count = self.selection.count_selected_rows()
        selected = count >= 1
        to_paste = len(self._to_cut) >= 1 or len(self._to_copy) >= 1
        self.paste.props.sensitive = not selected and to_paste and not self._busy
        self.new_folder.props.sensitive = not selected and not self._busy

    def _update_trash_tools(self):
        selected = self.selection.count_selected_rows() >= 1
        is_trash = default_trash.is_trash(self._history[self._index])
        self.restore_trash.props.sensitive = selected and is_trash
        self.delete_trash.props.sensitive = selected and is_trash

    def _update_rename(self):
        count = self.selection.count_selected_rows()
        sensitive = count == 1 and not self._editing and not self._busy
        self.rename.props.sensitive = sensitive

    def _update_detail(self):
        count = self.selection.count_selected_rows()
        sensitive = count == 1 and not self._editing and not self._busy
        self.detail.props.sensitive = sensitive

    def _update_directory_title(self):
        directory = self._history[self._index]

        if default_trash.is_trash(directory):
            name = PortfolioPlaces.XDG_TRASH_NAME
        else:
            name = os.path.basename(directory)

        self.headerbar.set_title(name)

    def _update_filter(self):
        self.filtered.refilter()
        self._update_content_stack()

        self._search_delay_handler_id = 0
        return GLib.SOURCE_REMOVE

    def _update_menu(self):
        self.menu_box.props.sensitive = not self._busy

    def _update_go_top_button(self, *args):
        alloc = self.get_allocation()
        reveal = self._adjustment.get_value() > (alloc.height / 2) and not self._editing
        self.go_top_revealer.props.reveal_child = reveal

    def _reset_search(self):
        self.search.set_active(False)
        self.search_entry.set_text("")
        self.search.grab_focus()

    def _on_open_started(self, worker):
        self._busy = True

        self.loading_label.set_text(_("Opening"))
        self.loading_bar.set_fraction(0.0)
        self.loading_details.props.visible = False
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

    def _on_open_updated(self, worker):
        self.loading_bar.pulse()

    def _on_open_finished(self, worker):
        self._busy = False
        self._clean_workers()
        self._update_all()

    def _on_open_failed(self, worker, path):
        self._busy = False
        self._clean_workers()

        name = os.path.basename(path)
        self.loading_description.set_text(_("Could not open %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_load_started(self, worker, directory):
        self._busy = True

        self.liststore.clear()

        self._update_directory_title()
        self._reset_search()
        self._update_all()

        self._load_delay_handler_id = GLib.timeout_add(
            self.LOAD_ANIMATION_DELAY,
            self._on_load_started_delayed,
        )

    def _on_load_started_delayed(self):
        self.loading_label.set_text(_("Loading"))
        self.loading_bar.set_fraction(0.0)
        self.loading_details.props.visible = False
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self._load_delay_handler_id = 0
        return GLib.SOURCE_REMOVE

    def _on_load_updated(self, worker, directory, found, index, total):
        for name, path, icon in found:
            row = self.liststore.append([icon, name, path])

            if self._to_select == path:
                self._to_select_row = row

            if self._to_go_to == path:
                self._to_go_to_row = row

        self.loading_bar.set_fraction((index + 1) / total)

    def _on_load_finished(self, worker, directory):
        self._busy = False
        self._clean_workers()
        self._clean_loading_delay()

        self._update_all()

        if self._to_select_row is not None:
            self._switch_to_selection_mode()
            self._select_and_go(self._to_select_row)
            self._to_select_row = None
            self._to_select = None
        elif self._to_go_to_row is not None:
            self._go_to(self._to_go_to_row)
            self._to_go_to_row = None
            self._to_go_to = None
        else:
            self._go_to_top()

    def _on_load_failed(self, worker, directory):
        self._busy = False
        self._clean_workers()
        self._clean_loading_delay()

        name = os.path.basename(directory)
        self.loading_label.set_text(_("Loading"))
        self.loading_description.set_text(_("Could not load %s") % name)
        self.content_stack.set_visible_child(self.loading_box)

        self._to_select_row = None
        self._to_select = None
        self._force_go_home = True
        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_clicked(self, treeview, event):
        result = self.treeview.get_path_at_pos(event.x, event.y)
        if result is None:
            return
        treepath, column, x, y = result
        self._last_clicked = treepath

    def _on_select(self, selection, model, treepath, selected, data=None):
        should_select = False

        if self._force_select is True:
            should_select = True
        elif treepath != self._last_clicked and selected:
            should_select = False
        elif treepath != self._last_clicked and not selected:
            should_select = False
        elif treepath == self._last_clicked and not selected:
            should_select = True
        elif treepath == self._last_clicked and selected:
            should_select = True

        if treepath == self._last_clicked:
            self._last_clicked = None
            self._dont_activate = True

        return should_select

    def _on_selection_changed(self, selection):
        if self._busy is True:
            return
        self._update_all()
        self._update_mode()

    def _on_go_previous(self, button):
        if self._index == 0:
            self._go_back_to_homepage()
        else:
            self._to_go_to = self._history[self._index]
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
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        path = model[treepath][self.PATH_COLUMN]
        self.show_properties(path)

    def _on_rename_clicked(self, button):
        self.name_cell.props.editable = True
        model, treepaths = self.selection.get_selected_rows()
        treepath = treepaths[-1]
        self.treeview.set_cursor_on_cell(
            treepath, self.name_column, self.name_cell, True
        )

    def _on_rename_started(self, cell_name, treepath, data=None):
        self._editing = True

        self._update_search()
        self._update_selection()
        self._update_selection_tools()
        self._update_go_top_button()

    def _on_rename_updated(self, cell_name, treepath, new_name, data=None):
        directory = self._history[self._index]
        new_path = os.path.join(directory, new_name)
        old_path = self._get_path(self.sorted, treepath)

        if new_path == old_path:
            self._on_rename_finished()
            return

        try:
            # respect empty folders
            if os.path.lexists(new_path):
                raise FileExistsError(_("%s already exists") % new_path)

            os.rename(old_path, new_path)

            _treepath = Gtk.TreePath.new_from_string(treepath)
            _treepath = self.sorted.convert_path_to_child_path(_treepath)
            _treepath = self.filtered.convert_path_to_child_path(_treepath)

            row = self.liststore.get_iter(_treepath)
            self.liststore.set_value(row, self.PATH_COLUMN, new_path)
            self.liststore.set_value(row, self.NAME_COLUMN, new_name)
        except Exception as e:
            logger.debug(e)
            self._notify(
                _("%s already exists") % new_name,
                None,
                self._on_popup_closed,
                None,
                True,
                None,
            )
            self._on_rename_clicked(None)
            return

        # remove this folder from history
        self._history = [
            path for path in self._history if not path.startswith(old_path)
        ]

        # take the user to the new position
        self._on_rename_finished()
        self._go_to_selection()

    def _on_rename_finished(self, *args):
        self.name_cell.props.editable = False
        self._editing = False
        self._update_all()

    def _on_delete_clicked(self, button):
        selection = self._get_selection()
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
        selection = self._get_selection()
        count = len(selection)

        self._to_cut = selection
        self._to_copy = []

        if count == 1:
            name = os.path.basename(selection[0][0])
            description = _("%s will be moved") % name
        else:
            description = _("%d files will be moved") % count

        self._notify(description, None, None, None, True, None)

        self._unselect_all()
        self._update_mode()

    def _on_copy_clicked(self, button):
        selection = self._get_selection()
        count = len(selection)

        self._to_copy = selection
        self._to_cut = []

        if count == 1:
            name = os.path.basename(selection[0][0])
            description = _("%s will be copied") % name
        else:
            description = _("%d files will be copied") % count

        self._notify(description, None, None, None, True, None)

        self._unselect_all()
        self._update_mode()

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

        self.loading_label.set_text(_("Pasting"))
        self.loading_bar.set_fraction(0.0)
        self.loading_details.props.visible = True
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

        self.liststore.append([icon, name, path])

    def _on_paste_updated(self, worker, path, index, total, current_bytes, total_bytes):
        description = os.path.basename(path)
        self.loading_description.set_text(description)
        self.loading_bar.set_fraction(index / total)

        human_current_bytes = utils.get_size_for_humans(current_bytes)
        human_total_bytes = utils.get_size_for_humans(total_bytes)
        self.loading_details.set_text(
            _("%s of %s") % (human_current_bytes, human_total_bytes)
        )

    def _on_paste_finished(self, worker, total):
        self._paste_finish()

    def _on_paste_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self._clean_progress()

        self._to_cut = []
        self._to_copy = []

        name = os.path.basename(path)
        self.loading_description.set_text(_("Could not paste %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_paste_stopped(self, worker):
        self._paste_finish()
        # XXX nuclear fix for when parent directorty doesn't get to be updated
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

        self.loading_label.set_text(_("Deleting"))
        self.loading_bar.set_fraction(0.0)
        self.loading_details.props.visible = False
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self.action_stack.set_visible_child(self.stop_box)
        self.tools_stack.set_visible_child(self.stop_tools)

    def _on_delete_pre_updated(self, worker, path):
        name = os.path.basename(path)
        self.loading_description.set_text(name)

    def _on_delete_updated(self, worker, path, ref, index, total):
        self._remove_row(ref)
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_delete_finished(self, worker, total):
        self._delete_finish()

    def _on_delete_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self._clean_progress()

        name = os.path.basename(path)
        self.loading_description.set_text(_("Could not delete %s") % name)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_delete_stopped(self, worker):
        self._delete_finish()

    def _on_popup_closed(self, button, popup, data):
        self._clean_popups()

    def _on_button_closed(self, button):
        self._clean_progress()
        self._unselect_all()
        self._update_all()
        self._update_mode()

        if self._force_go_home is False:
            return

        self._force_go_home = False
        self._go_back_to_homepage()

    def _on_stop_clicked(self, button):
        self.loading_label.set_text(_("Stopping"))
        self._worker.stop()

    def _on_select_all(self, button):
        self._select_all()
        self._update_mode()

    def _on_select_none(self, button):
        self._unselect_all()

    def _on_new_folder(self, button):
        directory = self._history[self._index]
        folder_name = utils.find_new_name(directory, _("New Folder"))
        path = os.path.join(directory, folder_name)

        try:
            Path(path).mkdir(parents=False, exist_ok=True)
        except Exception as e:
            logger.debug(e)
            self._notify(
                _("No permissions on this directory"),
                None,
                self._on_popup_closed,
                None,
                True,
                None,
            )
            return

        self._switch_to_selection_mode()

        icon = utils.get_file_icon(path)
        row = self.liststore.append([icon, folder_name, path])
        self._select_and_go(row, edit=True)

    def _on_restore_trash_clicked(self, button):
        selection = self._get_selection()
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

        self.loading_label.set_text(_("Restoring"))
        self.loading_bar.set_fraction(0.0)
        self.loading_details.props.visible = False
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self.action_stack.set_visible_child(self.stop_box)
        self.tools_stack.set_visible_child(self.stop_tools)

    def _on_restore_trash_pre_updated(self, worker, path):
        name = os.path.basename(path)
        self.loading_description.set_text(name)

    def _on_restore_trash_updated(self, worker, path, ref, index, total):
        self._remove_row(ref)
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_restore_trash_finished(self, worker, total):
        self._busy = False
        self._clean_workers()
        self._clean_progress()

        self._unselect_all()

        self._update_all()
        self._update_mode()

    def _on_restore_trash_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self._clean_progress()

        self.loading_description.set_text(_("Could not restore %s") % path)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_restore_trash_stopped(self, worker):
        self._delete_finish()

    def _on_delete_trash_clicked(self, button):
        selection = self._get_selection()
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

        self.loading_label.set_text(_("Deleting"))
        self.loading_bar.set_fraction(0.0)
        self.loading_details.props.visible = False
        self.content_stack.set_visible_child(self.loading_box)

        self._update_all()

        self.action_stack.set_visible_child(self.stop_box)
        self.tools_stack.set_visible_child(self.stop_tools)

    def _on_delete_trash_pre_updated(self, worker, path):
        name = os.path.basename(path)
        self.loading_description.set_text(name)

    def _on_delete_trash_updated(self, worker, path, ref, index, total):
        self._remove_row(ref)
        self.loading_bar.set_fraction((index + 1) / total)

    def _on_delete_trash_finished(self, worker, total):
        self._delete_finish()

    def _on_delete_trash_failed(self, worker, path):
        self._busy = False
        self._clean_workers()
        self._clean_progress()

        self.loading_description.set_text(_("Could not delete %s") % path)

        self.action_stack.set_visible_child(self.close_box)
        self.tools_stack.set_visible_child(self.close_tools)

    def _on_delete_trash_stopped(self, worker):
        self._delete_finish()

    def _on_row_activated(self, treeview, treepath, treecolumn, data=None):
        if self._dont_activate is True:
            self._dont_activate = False
            return
        if self.selection.get_mode() == Gtk.SelectionMode.NONE:
            path = self._get_path(self.sorted, treepath)
            self._move(path)

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
        self._clean_passphrase()
        self._encrypted = encrypted
        self.passphrase_header.props.title = encrypted.get_friendly_label()
        self.content_deck.set_visible_child(self.files_stack)
        self.files_stack.set_visible_child(self.passphrase_box)
        self.passphrase_entry.grab_focus()

    def _on_passphrase_back_clicked(self, button):
        self._clean_passphrase()
        self.content_deck.set_visible_child(self.places_box)

    def _on_passphrase_activate(self, button):
        self.passphrase_entry.props.sensitive = False
        self.passphrase_label.props.visible = False
        self.passphrase_spinner.props.visible = True
        self.passphrase_spinner.props.active = True

        passphrase = self.passphrase_entry.get_text()
        self._encrypted.unlock(passphrase, self._on_places_unlock_finished)

    def _on_places_unlock_finished(self, device, encrypted, success):
        self._clean_passphrase()

        if device is None:
            logger.debug(f"Failed to unlock {encrypted}")
        elif not os.access(device.mount_point, os.R_OK):
            logger.debug(f"No permissions for {device}")
        elif success is True:
            self._reset_to_path(device.mount_point)
            self._go_to_files_view(duration=200)
            return

        self._encrypted = encrypted
        self.passphrase_entry.grab_focus()
        self.passphrase_label.set_text(_("Sorry, that didn't work"))

    def _on_help_clicked(self, button):
        Gio.AppInfo.launch_default_for_uri("https://github.com/tchx84/Portfolio", None)

    def _on_about_clicked(self, button):
        self.about_deck.set_visible_child(self.about_box)

    def _on_about_back_clicked(self, button):
        self.about_deck.set_visible_child(self.content_deck)

    def _on_properties_back_clicked(self, button):
        self.content_deck.set_visible_child(self.files_stack)

    def _on_long_pressed(self, gesture, x, y):
        if self.selection.get_mode() == Gtk.SelectionMode.MULTIPLE:
            return

        self._switch_to_selection_mode()
        path = self.treeview.get_path_at_pos(x, y)

        if path is None:
            self._switch_to_navigation_mode()
            return

        treepath = path[0]
        self.selection.select_path(treepath)

        # because of the custom selection rules, is not guaranteed
        # that this will actually be selected so always update mode.
        self._update_mode()

    def _on_hidden_toggled(self, button):
        self._settings.show_hidden = self.show_hidden_button.props.active
        self._refresh()

    def _on_sort_toggled(self, button):
        if self.a_to_z_button.props.active:
            self._settings.sort_order = PortfolioSettings.ALPHABETICAL_ORDER
        else:
            self._settings.sort_order = PortfolioSettings.MODIFIED_TIME_ORDER

        self._refresh()

    def _on_menu_button_clicked(self, button):
        button.props.popover = self.menu_popover
        self.menu_popover.popup()

    def _on_content_folded(self, deck, data=None):
        child = self.content_deck.get_visible_child()
        if child == self.places_box and self._worker is not None:
            self._worker.stop()
            self._clean_workers()
        elif child == self.files_box:
            self._properties.stop()

    def _on_shutdown(self, window):
        if self._worker is not None:
            self._worker.stop()
        self._properties.stop()

    def open(self, path=PortfolioPlaces.PORTFOLIO_HOME_DIR, force_page_switch=False):
        path = utils.get_uri_path(path)

        # make sure it exists though !
        if not os.path.exists(path):
            logger.warning(_("Could not open %s") % path)
            return

        # if it's a file then use its parent folder
        if not os.path.isdir(path):
            self._to_select = path
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
        self._properties.props.path = path

        if force_page_switch is True:
            self.open(path, force_page_switch)

        self.content_deck.set_visible_child(self.properties_box)
