# Changelog

## [unreleased]

- Fixed issues in systems without glibc by @craftyguy.
- Added German translation by @lqs01.

## [0.9.10] 2021-03-01

- Fixed all blockers to enable portrait mode.
- Fixed a few cases where the selection mode would incorrectly activate.
- Fixed stopping operations to immediately cancel the current operation.
- Fixed categories and keywords to make Portfolio easier to find, by @philipzae.
- Added Brazilian Portuguese translation by @rffontenelle.
- Added home page with places and devices, designed by @nahuelwexd.
- Added file properties viewer.
- Added eject button for external storage devices.
- Changed folder loading behavior to only display the progress bar if loading too slow.

## [0.9.9] 2021-02-10

- Fixed setting the proper selection mode while switching Places.
- Added support for org.freedesktop.FileManager1 interface.
- Added Czech translation by @AsciiWolf.
- Added more tests, tests, tests.

## [0.9.8] 2021-02-04

- Fixed missing Exec field code in desktop file by @henry-nicolas.

## [0.9.7] 2021-02-03

- Fixed gradients in the application icon by @bertob.

## [0.9.6] 2021-01-25

- Added support for stopping paste and delete operations.
- Added support for opening folders as CLI arguments.
- Added more tests, tests, tests.

## [0.9.5] 2021-01-18

- Fixed repeated places, e.g. "System" and "root".
- Fixed catching an edge-case permission error, while deleting.
- Fixed delete worker for smoother feedback, while deleting.
- Added visual feedback when opening files.
- Added more tests, tests, tests.
- Updated all translations by @vistaus, @cho2, @eson57 and @GNUuser.

## [0.9.4] 2021-01-11

- Fixed catching permissions errors while loading by @Avolpe.
- Added more detailed feedback to pasting and deleting screens.
- Added credits section to about "dialog".
- Added more tests, tests, tests.

## [0.9.3] 2021-01-04

- Fixed regression where the last unselected row would unexpectedly activate.
- Fixed to kick-back to HOME when the external drive is unmounted.
- Fixed page will no longer do full reload after deleting only a few files.
- Added sorting options to the menu.
- Added floating button to go back to the top and to save multiple swipes.
- Added enhanced icon by @bertob.
- Added i18n support.
- Added Spanish translation.
- Added Swedish translation by @eson57.
- Added Indonesian translation by @cho2.
- Added Dutch translation by @vistaus.
- Changed paste to behave like other commonly used file managers.

## [0.9.2] 2020-12-28

- Fixed performance issues with big folders.
- Fixed styling issues with menu items.
- Fixed about "dialog" headerbar "weirdness".
- Fixed issues with OSK ocluding action bar.
- Fixed icon not showing on Phosh.
- Fixed notifications on missing permissions.
- Added auto-scroll to newly created folder or renamed file.
- Added no-results page for search.
- Added show hidden files menu filter.
- Added show OS root directory in places.
- Added tests, tests, tests.

## [0.9.1] 2020-12-21

- Fixed assigning old paths to copied rows.

## [0.9.0] 2020-12-20

- Added support for browsing HOME and external volumes directories.
- Added support for opening files.
- Added support for multi-selection of files and directories.
- Added support for moving, copying and pasting files and directories.
- Added support for creating of new directories.
- Added support for renaming files and directories.
