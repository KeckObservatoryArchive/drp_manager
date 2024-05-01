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
##### RTI Stuff
###


def alert_RTI(directory, pargs, cfg):

    def get_url(url, data):
        try:
            res = requests.get(url,
                               params = data, 
                               auth = (cfg['RTI']['user'], cfg['RTI']['pass']))
            print(f"Sending {res.request.url}")
        except requests.exceptions.RequestException as e:
            print(f"Error caught while posting to {url}:")
            print(e)
            return None
        return res
    
    # data_directory = pargs.output + "/pypeit_files"
    
    print(f"Alerting RTI that {directory} is ready for ingestion")

    url = cfg['RTI']['url']

    data = {
        'instrument': pargs.inst,
        # 'koaid': "KOAID_HERE", # PypeIt files are found from datadir, not koaid
        'ingesttype': cfg['RTI']['rti_ingesttype'],
        'datadir': str(directory),
        'start': str(cfg.start_time),
        'reingest': cfg['RTI']['rti_reingest'],
        'testonly': cfg['RTI']['rti_testonly'],
        'dev': cfg['RTI']['rti_dev']
    }
    
   
    res = get_url(url, data)
    

###
##### Script Stuff
###

def get_config(cfg_file):

    cfg = ConfigParser()
    cfg.read(cfg_file)
    
    inst_options = cfg['INSTRUMENTS']['keck_inst_names'].split(' ')
    inst_pypeit = cfg['INSTRUMENTS']['pypeit_inst_names'].split(' ')
    inst_roots = cfg['INSTRUMENTS']['roots'].split(' ')
    cfg.inst_opts = {
        inst_options[i] : {
            'pypeit_name' : inst_pypeit[i],
            'root' : inst_roots[i]
        }
    for i in range(len(inst_options))}

    cfg.start_time = datetime.utcnow()

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
    
    parser.add_argument('-r', '--root', dest='root',
                        help='Base root of the files. Must be [KB, KR, kb, kr]')
    
    parser.add_argument('-c', '--config', dest='cfg',default='./kcwi.ini',
                        help='Configuration file to use. Defaults to kcwi.ini')

    
    
    pargs =  parser.parse_args()

    return pargs

def get_config(cfg_file):

    cfg = ConfigParser()
    cfg.read(cfg_file)

    return cfg

def main():
    
    # Parse the arguments
    pargs = get_parsed_args()

    cfg = get_config(pargs.cfg)

    print("Creating red and blue output dirs...")    
    os.makedirs(pargs.output + "/red", exist_ok=True)
    os.makedirs(pargs.output + "/blue", exist_ok=True)

    if pargs.level == 'lev1':
        red_cmd = cfg['lev1']['red_cmd']
        blue_cmd = cfg['lev1']['blue_cmd']
    else:
        red_cmd = cfg['lev2']['red_cmd']
        blue_cmd = cfg['lev2']['blue_cmd']

    print("Running red and blue commands:")
    print("Red command: " + red_cmd)
    print("Blue command: " + blue_cmd)
    
    try:
        subprocess.Popen(red_cmd.split(" "), cwd=pargs.output + "/red")
        subprocess.Popen(blue_cmd.split(" "), cwd=pargs.output + "/blue")
        pass
    except Exception as e:
        print('Error running command: ' + str(e))
    print("done")
    

if __name__ == '__main__':
    main()
