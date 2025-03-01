# Portfolio ![CI](https://github.com/tchx84/Portfolio/workflows/CI/badge.svg)

<img height="100" src="https://github.com/tchx84/Portfolio/blob/master/data/dev.tchx84.Portfolio.svg">

A minimalist file manager for those who want to use Linux mobile devices.

## Usage

Tap to activate and long press to select, to browse, open, copy, move, delete, or edit your files.

## Get it

[<img width="240" src="https://flathub.org/assets/badges/flathub-badge-i-en.png">](https://flathub.org/apps/details/dev.tchx84.Portfolio)

## Build it yourself

```
git clone https://github.com/tchx84/Portfolio.git
cd Portfolio
flatpak install --user org.gnome.{Platform,Sdk}//47
flatpak-builder --user --force-clean --install build dev.tchx84.Portfolio.json
flatpak run --branch=master dev.tchx84.Portfolio
```

This app is powered by [Builder](https://flathub.org/apps/details/org.gnome.Builder) and [Glade](https://flathub.org/apps/details/org.gnome.Glade).

## Contribute

If you are interested in contributing to this project just send a pull request to [this](https://github.com/tchx84/Portfolio) repo.

## Disclaimer

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](COPYING) for more details.
