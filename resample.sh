#!/bin/bash

# This script resamples all audio files in the current directory from 8000 Hz to 16000 Hz

for file in *.wav
do
  echo "Processing $file..."
  sox "$file" -r 16000 "${file%.*}_16k.wav"
  rm $file
done
