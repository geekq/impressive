#!/usr/bin/sh
xrandr --output TMDS-1 --off
xrandr --output LVDS --auto
xrandr --output VGA --mode 1024x768 --right-of LVDS

