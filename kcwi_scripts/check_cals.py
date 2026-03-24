#!/usr/local/anaconda/bin/python

import argparse
import datetime as dt
import subprocess as sp
from configparser import ConfigParser
import yaml

def check_cals(color, cron=False):
    files = {"blue":"KB", "red":"KR"}

    utdate = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")

    cfg = ConfigParser()
    cfg.read("/drp/manager/default/kcwi_scripts/kcwi.ini")
    cmd      = cfg["cmd"]["checkcals_path"]

    with open('/drp/manager/default/drp_config.live.ini') as f: drp = yaml.safe_load(f)
    config = drp["KCWI"]["CONFIG_LEV1"]

    files    = f"/koadata/KCWI/{utdate}/lev0/{files[color]}*.fits"
    full_cmd = f"{cmd} -c {config} {files}"
    if cron:
        full_cmd += " -a"
    p = sp.Popen(full_cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
    p.wait()
    (err, output) = p.communicate()
    return err, output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check KCWI calibrations")
    parser.add_argument("color", help="blue or red")
    args = parser.parse_args()

    if args.color not in ["blue", "red"]:
        print("Parameter value must be blue or red")
        exit()

    output = check_cals(args.color)
    print(output)

