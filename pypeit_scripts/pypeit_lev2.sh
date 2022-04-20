#!/usr/bin/sh

export PATH=$HOME/.conda/envs/pypeit/bin:/usr/sbin:/usr/bin:/sbin:/binmes
DATE=`date -u '+%Y%m%d'`
INSTRUMENT=`echo $1 | tr '[a-z]' '[A-Z]'`
LEV0DATA="/koadata/$INSTRUMENT/$DATE/lev0"
RUN=true
case $INSTRUMENT in
  DEIMOS)
    PREFIX='DE.'
    ;;
  MOSFIRE)
    PREFIX='MF.'
    ;;
  *)
    RUN=false
    ;;
esac
if [ ! -d $LEV0DIR ]; then
  echo "No lev0 data found in $LEV0DATA"
  RUN=false
fi      
if [ "$RUN" ]; then
  cd /drp/manager/default/pypeit_scripts
  python pypeit_lev2.py $INSTRUMENT -i /koadata/$INSTRUMENT/$DATE/lev0 -r $PREFIX -o /k2drpdata/${INSTRUMENT}_DRP/$DATE -n 10 
fi
