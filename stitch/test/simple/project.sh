clear
rm -rf /tmp/*.pto /tmp/*.jpg /tmp/pr0ntools*
time python -u $(which pr0nstitch) --result=out.pto *.jpg 2>&1 |tee log.txt
cat log.txt |fgrep -i master
