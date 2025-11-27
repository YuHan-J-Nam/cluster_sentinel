#!/bin/bash

TEMP=temp_results.txt

for i in `seq 100`; do
	# echo "Loop $i"
	python npNsphereVolume.py >> $TEMP & # Adding the & runs it in bg and parallel
done

# echo $0 $1 $2
#NCPU=`nproc`
#seq 100 | xargs -L1 -P$NCPU ./npNsphereVolume.py
#
#wait

# Process results
# cat $TEMP | awk 'BEGIN{print "Starting Calculation..."} {print $1*$2/$3} END{print "Calculation finished"}'  # You can print beginning and end statements
cat $TEMP | awk 'BEGIN{print "aSqr=0.0;nAccept=0;nTotal=0"} {aSqr=$1; nAccept += $2; nTotal += $3;} END{print aSqr" "nAccept" "nTotal" "aSqr*nAccept/nTotal}'
