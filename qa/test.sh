#!/bin/bash

# stop on error, and echo commands to stdout
set -ex

black --check src
