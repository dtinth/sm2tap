#!/bin/bash
# simple shell script that does these 3 commands in one

CONVERTPY=`dirname .`/convert.py

if [ "$1$2" = "" ]; then

	echo "Usage: $0 file.sm file.tapd" >&2

else

	plutil -convert xml1 "$2"
	python "$CONVERTPY" "$1" "$2"
	plutil -convert binary1 "$2"

fi
