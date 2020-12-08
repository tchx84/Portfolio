# Portfolio

A minimalist file manager for Linux mobile devices.

## Build it yourself

```
$ git clone https://github.com/tchx84/Portfolio.git
$ cd Portfolio
$ flatpak-builder --force-clean --repo=repo build dev.tchx84.Portfolio.json
$ flatpak build-bundle repo portfolio.flatpak dev.tchx84.Portfolio
$ flatpak install portfolio.flatpak
```

## Note

This is just another weekend project, barely a prototype, but I will improve it over time. Currently, it allows you to browse your home directory, search, open, rename and delete files.

The reason I am creating yet another files manager is because my experience browsing files on my Pinephone has not been great and I wanted to build something for my own use and learn.

## Disclaimer

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](COPYING) for more details.
