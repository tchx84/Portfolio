#!/usr/bin/env bash

pyflakes src && \
black --check src
