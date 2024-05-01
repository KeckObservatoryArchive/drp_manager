#!/bin/sh

DATE=`date -u '+%Y%m%d'`
INSTRUMENT=`echo $1 | tr '[a-z]' '[A-Z]'`

export PATH=$HOME/.conda/envs/kcwidrp/bin:/usr/sbin:/usr/bin:/sbin:/bin
LEV0DATA="/koadata/KCWI/$DATE/lev0"
RUN=true
OUTPUTDIR='/k2drpdata'

if [ ! -d $LEV0DIR ]
then
  echo "No lev0 data found in $LEV0DATA"
  RUN=false
fi      
if [ "$RUN" ]
then
  cd /drp/manager/default/kcwi_scripts
  python start_kcwi.py lev1 -i /koadata/test/$INSTRUMENT/$DATE/lev0 -o $OUTPUTDIR/${INSTRUMENT}_DRP/$DATE
fi
