#!/bin/bash

# stop on error, and echo commands to stdout
set -ex

pyflakes src
black --check src
