#!/bin/bash
set -e
INPUT=$1
SERVER=$2
FILE=Gottesdienst
WAV=/tmp/$FILE.wav

rm -f /tmp/$FILE.{wav,ulaw,sln,gsm}

lame --mp3input --decode "$INPUT" $WAV
sox -V $WAV -r 8000 -c 1 -t ul /tmp/$FILE.ulaw
sox $WAV --rate 8000 --channels 1 --type raw /tmp/$FILE.sln
sox $WAV -r 8000 -c 1 -t gsm /tmp/$FILE.gsm

echo "Uploading to $SERVER..."
scp $WAV "$SERVER":/var/lib/asterisk/sounds/de_DE/custom/
scp /tmp/$FILE.ulaw "$SERVER":/var/lib/asterisk/sounds/de_DE/custom/
scp /tmp/$FILE.sln "$SERVER":/var/lib/asterisk/sounds/de_DE/custom/
scp /tmp/$FILE.gsm "$SERVER":/var/lib/asterisk/sounds/de_DE/custom/
