# Portfolio

A minimalist file manager for those who want to use Linux mobile devices.

## Build it yourself

```
$ git clone https://github.com/tchx84/Portfolio.git
$ cd Portfolio
$ flatpak-builder --force-clean --repo=repo build dev.tchx84.Portfolio.json
$ flatpak build-bundle repo portfolio.flatpak dev.tchx84.Portfolio
$ flatpak install portfolio.flatpak
```

## Disclaimer

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](COPYING) for more details.
