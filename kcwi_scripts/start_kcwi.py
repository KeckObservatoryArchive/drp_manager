from datetime import datetime
from pathlib import Path
import os
import sys
import requests
from multiprocessing import Pool
from argparse import ArgumentParser
from configparser import ConfigParser
import subprocess

###
##### Script Stuff
###

def get_config(cfg_file):

    cfg = ConfigParser()
    print("Reading " + cfg_file)
    cfg.read(cfg_file)

    return cfg

def get_parsed_args():
    """Returns the parsed command line arguments

    Returns
    -------
    argparse NameSpace
        contains all of the parsed arguments
    """
    
    parser = ArgumentParser()
    
    # If nothing else is supplied, script will look for data in cwd
    default_input = os.getcwd()
    default_output = os.path.join(default_input, "redux")

    parser.add_argument('level', type=str, choices=['lev1', 'lev2'], help='Level of reduction to perform')

    parser.add_argument('-i', '--input-dir', dest='input', 
                        default=default_input,
                        help='Path to raw files. Defaults to current directory')
    
    parser.add_argument('-o', '--output-dir', dest='output',
                        default=default_output,
                        help='Directory to put output in. Defaults to ./redux')
    
    parser.add_argument('-c', '--config', dest='cfg',default='./kcwi.ini',
                        help='Configuration file to use. Defaults to kcwi.ini')
    
    parser.add_argument('--rti-cfg', dest='rti_cfg', default='./rti.ini', 
                        help='RTI configuration file to use. Defaults to rti.ini')
    parser.add_argument('--drp-cfg', dest='drp_cfg', help='DRP configuration file to use.')

    
    
    pargs =  parser.parse_args()

    return pargs

def alert_RTI(cfg, date):

        
    data = {
        'instrument': "KCWI",
        'ingesttype': "lev2",
        'utdate' : date,
        'testonly': "true",
        'dev': "true"
    }
    
    try:
        res = requests.get(cfg['rti']['url'],
                            params = data, 
                            auth = (cfg['rti']['rti_user'], cfg['rti']['rti_pass']))
        print(f"Sent {res.request.url}")
        print(f"Response:\n{res.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error caught while GETing to {cfg['rti']['url']}:")
        print(e)
        print("Continuing without alerting RTI")
        return None
    return res


def run_cmd(cmd, cwd):
    subprocess.Popen(cmd.split(" "), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, cwd=cwd)


def main():
    
    # Parse the arguments
    pargs = get_parsed_args()

    cfg = get_config(pargs.cfg)

    print("Creating red and blue output dirs...")    
    os.makedirs(pargs.output + "/red", exist_ok=True)
    os.makedirs(pargs.output + "/blue", exist_ok=True)

    red_cmd = cfg['cmd']['cmd_path'] + " "
    blue_cmd = cfg['cmd']['cmd_path'] + " "

    if pargs.level == 'lev1':
        red_cmd += cfg['lev1']['red_cmd']
        blue_cmd += cfg['lev1']['blue_cmd']
    else:
        red_cmd += cfg['lev2']['red_cmd']
        blue_cmd += cfg['lev2']['blue_cmd']
    
    red_cmd = red_cmd.replace("DIRECTORY", pargs.input)
    blue_cmd = blue_cmd.replace("DIRECTORY", pargs.input)

    red_cmd = red_cmd.replace("DRP_CONFIG", pargs.drp_cfg)
    blue_cmd = blue_cmd.replace("DRP_CONFIG", pargs.drp_cfg)

    red_cmd = red_cmd.replace("RTI_CONFIG", pargs.rti_cfg)
    blue_cmd = blue_cmd.replace("RTI_CONFIG", pargs.rti_cfg)

    print("Running red and blue commands:")
    print("Red command: " + red_cmd)
    print("Blue command: " + blue_cmd)
    
    if pargs.level == 'lev2':
        try:
            with Pool(processes=2) as pool:
                pool.starmap(func=run_cmd, iterable=[(red_cmd, pargs.output + "/red"), (blue_cmd, pargs.output + "/blue")])
            alert_RTI(cfg, datetime.now().strftime("%Y%m%d"))
        except Exception as e:
            print('Error running command: ' + str(e))
    else: # lev1
        try:
            run_cmd(red_cmd, pargs.output + "/red")
            run_cmd(blue_cmd, pargs.output + "/blue")
            # subprocess.Popen(red_cmd.split(" "), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, cwd=pargs.output + "/red")
            # subprocess.Popen(blue_cmd.split(" "), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, cwd=pargs.output + "/blue")
        except Exception as e:
            print('Error running command: ' + str(e))

    print("done")


if __name__ == '__main__':
    main()
