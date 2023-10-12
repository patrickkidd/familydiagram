#!/bin/sh

FILE="${SRCROOT}/HockeySDK-Mac/BuildAgent"
if [ -f "$FILE" ]; then
    "$FILE"
fi
