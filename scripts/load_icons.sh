#!/bin/bash

# Define the source directory
src=$1
dest=$2

open_sprite='<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" aria-hidden="true">'
symbols=''
end_sprite='</svg>'

# Check if the source is not a directory
if [ ! -d "$src" ]; then
  echo "$1 is not a directory"
  exit 1
fi

# Check if the destination is not a file
if [ ! -f "$dest" ] || [ $dest == *.svg ]; then
  echo "$1 is not a directory"
  exit 1
fi

# Loop through files in the source directory
for file in "$src"/*.svg; do
  if [ -f "$file" ]; then
    symbols+="\n$(<$file)\n"
  fi
done

echo -e "${open_sprite}${symbols}${end_sprite}" > $dest
