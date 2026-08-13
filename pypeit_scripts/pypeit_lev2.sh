#!/bin/sh

echo "Script launched at $(date)"

# DATE is the current UT date
DATE=`date -u '+%Y%m%d'`
#DATE="20250228"

# INSTRUMENT is passed in on the command line
INSTRUMENT=`echo $1 | tr '[a-z]' '[A-Z]'`

# Get TelNr
TELNR=`hostname | cut -c1-2`
if [ "$TELNR" != "k1" ] && [ "$TELNR" != "k2" ]
then
  echo "k1 or k2? "
  read TELNR
fi

# Conda environment location
#ENV="$HOME/.conda/envs"
ENV="/drp/envs"

if [ $# -ge 2 ] && [ "$2" != "--calibonly" ]
then
    PYPEIT_VERSION="pypeit_$2"
fi
if [ ! -d "$ENV/$PYPEIT_VERSION/bin" ]; then
	echo "No conda environment matching $PYPEIT_VERSION found!"
fi
export PATH=$ENV/$PYPEIT_VERSION/bin:/usr/sbin:/usr/bin:/sbin:/bin
LEV0DATA="/koadata/$INSTRUMENT/$DATE/lev0"
RUN=true
if [ ! -d $LEV0DIR ]
then
  echo "No lev0 data found in $LEV0DATA"
  RUN=false
fi      

# Determine if this is a calibration only run
CALIB=''
if [ "$2" = "--calibonly" ] || [ "$3" = "--calibonly" ]
then
    CALIB="--calibonly"
fi

# Set OUTPUTDIR
OUTPUTDIR="/${TELNR}drpdata/${INSTRUMENT}_DRP/$DATE"

# Start PypeIt
if [ "$RUN" ]
then
  echo "Input Data Directory: /koadata/$INSTRUMENT/$DATE/lev0"
  echo "Output Data Directory: $OUTPUTDIR"
  echo "PypeIt Version: $PYPEIT_VERSION"
  echo "PATH: $PATH"
  cd /drp/manager/default/pypeit_scripts
  python pypeit_lev2.py $INSTRUMENT -i /koadata/$INSTRUMENT/$DATE/lev0 -o $OUTPUTDIR -n 10 $CALIB
fi
