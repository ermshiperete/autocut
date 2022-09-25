#!/bin/bash
ANNOUNCEFILE=$1
KEY=$2
SERVER=$3
FILE=Announce
WAV=/tmp/$FILE.wav

TEXT=$(cat $ANNOUNCEFILE)
wget --output-document=$WAV http://api.voicerss.org/?key=${KEY}\&hl=de-de\&v=Lina\&src="$TEXT"

sox -V $WAV -r 8000 -c 1 -t ul /tmp/$FILE.ulaw
sox $WAV --rate 8000 --channels 1 --type raw /tmp/$FILE.sln
sox $WAV -r 8000 -c 1 -t gsm /tmp/$FILE.gsm

echo "Uploading to $SERVER..."
scp $WAV $SERVER:/var/lib/asterisk/sounds/de_DE/custom/
scp /tmp/$FILE.ulaw $SERVER:/var/lib/asterisk/sounds/de_DE/custom/
scp /tmp/$FILE.sln $SERVER:/var/lib/asterisk/sounds/de_DE/custom/
scp /tmp/$FILE.gsm $SERVER:/var/lib/asterisk/sounds/de_DE/custom/
