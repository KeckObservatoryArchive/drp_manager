#!/usr/bin/bash

logfile=$(date +%Y%m%d)
logfile="/drp/logs/quicklook/$logfile.log"
echo $logfile

/usr/local/anaconda3/bin/conda run -n pypeit_ql --live-stream ginga --loglevel=20 --stderr --log "$logfile"