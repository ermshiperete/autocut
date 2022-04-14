#!/bin/bash
INPUT=$1
SERVER=$2
FILE=Gottesdienst
WAV=/tmp/$FILE.wav
LOGFILE=/tmp/copyGd.log
DEBUGFILE=/tmp/copyGd.debug

rm -f /tmp/$FILE.{wav,ulaw,sln,gsm}
echo "----------------------" >> $LOGFILE
echo "----------------------" >> $DEBUGFILE

lame --mp3input --decode "$INPUT" $WAV  >> $LOGFILE 2>>$DEBUGFILE
sox -V $WAV -r 8000 -c 1 -t ul /tmp/$FILE.ulaw  >> $LOGFILE 2>>$DEBUGFILE
sox $WAV --rate 8000 --channels 1 --type raw /tmp/$FILE.sln >> $LOGFILE 2>>$DEBUGFILE
sox $WAV -r 8000 -c 1 -t gsm /tmp/$FILE.gsm >> $LOGFILE 2>>$DEBUGFILE

scp $WAV $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
scp /tmp/$FILE.ulaw $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
scp /tmp/$FILE.sln $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
scp /tmp/$FILE.gsm $SERVER:/var/lib/asterisk/sounds/de_DE/custom/ >> $LOGFILE 2>>$DEBUGFILE
