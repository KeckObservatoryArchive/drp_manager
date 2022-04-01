#!/usr/bin/sh

export PATH=$HOME/anaconda3/envs/pypeit/bin:/usr/sbin:/usr/bin:/sbin:/binmes
DATE=`date -u '+%Y%m%d'`
INSTRUMENT=`echo $1 | tr '[a-z]' '[A-Z]'`
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
if "$RUN"; then
  python /drp/manager/default/pypeit_scripts/pypeit_lev2.py $INSTRUMENT -i /koadata/$INSTRUMENT/$DATE/lev0 -r $PREFIX -o /k2drpdata/${INSTRUMENT}_DRP/$DATE -n 10 
fi
