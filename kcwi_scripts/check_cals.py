#!/usr/local/anaconda/bin/python

import argparse
import datetime as dt
import subprocess as sp

def check_cals(color, cron=False):
    files = {"blue":"KB", "red":"KR"}

    utdate = dt.datetime.utcnow().strftime("%Y%m%d")

    cmd      = "/home/kcwidrp/.conda/envs/default/bin/check_cals"
    config   = "/k2drpdata/KCWI_DRP/configs/kcwi_lev1.cfg"
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

