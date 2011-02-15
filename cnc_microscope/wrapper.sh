#!/bin/bash

TEMP_FILE=/tmp/microscope.ngc
#HOST=uvforge
HOST=192.168.1.108

python pr0ncnc.py 2>$TEMP_FILE >$TEMP_FILE
if [ $? -ne 0 ]
then
	cat $TEMP_FILE |head -n 30
	rm $TEMP_FILE
	exit
fi

echo 'Uploading'
scp $TEMP_FILE mcmaster@$HOST:/home/mcmaster/NGC/wafer/cur.ngc
UPLOADED_DIR=$(python -c "import time; print '%s' % time.strftime('uploaded/%d_%m_%Y__%H_%M_%S')")
echo "Copying data files to $UPLOADED_DIR"
mkdir $UPLOADED_DIR
mv $TEMP_FILE $UPLOADED_DIR/
python pr0ncnc.py --json >$UPLOADED_DIR/cur.json
cp microscope.json $UPLOADED_DIR/
cp scan.json $UPLOADED_DIR/

