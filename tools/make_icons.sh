#!/bin/sh
# Raster icons from favicon.svg (the ring mark the pages and the app use), with ImageMagick 7:
#   favicon.ico            16, 32 and 48 px, rounded square on transparent corners
#   apple-touch-icon.png   180 px, full square (iOS rounds the corners itself)
#   img/stima-logo-512.png 512 px, full square: the Organization logo in the JSON-LD (tools/site_meta.py)
# favicon.svg draws the ring as two filled circles, not a stroke: ImageMagick's own SVG renderer drops stroked
# circles, and browsers draw both the same. The output carries no timestamps, so a rerun gives the same bytes.
#   sh tools/make_icons.sh
set -eu
cd "$(dirname "$0")/.."
PNG="-strip -depth 8 -define png:exclude-chunks=date,time"
magick -density 1536 -background none favicon.svg -define icon:auto-resize=48,32,16 favicon.ico
magick -density 1536 -background '#2A103A' favicon.svg -flatten -resize 180x180 $PNG apple-touch-icon.png
magick -density 1536 -background '#2A103A' favicon.svg -flatten -resize 512x512 $PNG img/stima-logo-512.png
