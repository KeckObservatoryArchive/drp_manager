#!/bin/sh
echo "Script launched at $(date)"
DATE=`date -u '+%Y%m%d'`
INSTRUMENT=`echo $1 | tr '[a-z]' '[A-Z]'`
if [ $# -ge 2 ] && [ "$2" != "--calibonly" ]
then
    PYPEIT_VERSION="pypeit_$2"
fi
if [ ! -d "$HOME/.conda/envs/$PYPEIT_VERSION/bin" ]; then
	echo "No conda environment matching $PYPEIT_VERSION found!"
fi
export PATH=$HOME/.conda/envs/$PYPEIT_VERSION/bin:/usr/sbin:/usr/bin:/sbin:/bin
LEV0DATA="/koadata/$INSTRUMENT/$DATE/lev0"
RUN=true
case $INSTRUMENT in
  DEIMOS)
    PREFIX='DE.'
    OUTPUTDIR='/k2drpdata'
    ;;
  MOSFIRE)
    PREFIX='MF.'
    OUTPUTDIR='/k1drpdata'
    ;;
  NIRES)
    PREFIX='NR.'
    OUTPUTDIR='/k2drpdata'
    ;;
  ESI)
    PREFIX='ES.'
    OUTPUTDIR='/k2drpdata'
    ;;
  *)
    RUN=false
    ;;
esac
if [ ! -d $LEV0DIR ]
then
  echo "No lev0 data found in $LEV0DATA"
  RUN=false
fi      
CALIB=''
if [ "$2" = "--calibonly" ] || [ "$3" = "--calibonly" ]
then
    CALIB="--calibonly"
fi
if [ "$RUN" ]
then
  echo "Input Data Directory: /koadata/$INSTRUMENT/$DATE/lev0"
  echo "Output Data Directory: $OUTPUTDIR/${INSTRUMENT}_DRP/$DATE"
  echo "PypeIt Version: $PYPEIT_VERSION"
  echo "PATH: $PATH"
  cd /drp/manager/default/pypeit_scripts
  python pypeit_lev2.py $INSTRUMENT -i /koadata/$INSTRUMENT/$DATE/lev0 -r $PREFIX -o $OUTPUTDIR/${INSTRUMENT}_DRP/$DATE -n 10 $CALIB
fi
