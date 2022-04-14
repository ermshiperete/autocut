#!/bin/bash
ANNOUNCEFILE=$1
KEY=$2
SERVER=$3
LOGFILE=/tmp/copyGd.log
DEBUGFILE=/tmp/copyGd.debug
FILE=Announce
WAV=/tmp/$FILE.wav

TEXT=$(cat $ANNOUNCEFILE)
wget --output-document=$WAV http://api.voicerss.org/?key=${KEY}\&hl=de-de\&v=Lina\&src="$TEXT"  >> $LOGFILE 2>>$DEBUGFILE

sox -V $WAV -r 8000 -c 1 -t ul /tmp/$FILE.ulaw >> $LOGFILE 2>>$DEBUGFILE
sox $WAV --rate 8000 --channels 1 --type raw /tmp/$FILE.sln >> $LOGFILE 2>>$DEBUGFILE
sox $WAV -r 8000 -c 1 -t gsm /tmp/$FILE.gsm >> $LOGFILE 2>>$DEBUGFILE

scp $WAV $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
scp /tmp/$FILE.ulaw $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
scp /tmp/$FILE.sln $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
scp /tmp/$FILE.gsm $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
