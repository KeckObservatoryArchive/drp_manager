'''
Script to manage single instance of a level2 pipeline (start/stop/restart)

NOTE: Script is currently designed to assume this file exists
in same directory as python module it wil start.

Example use:
python lev2_manager.py instrument start|stop|restart|status [--utdate yyyymmdd] [--skip_avail]
    --skip_avail will skip the instrument availability check and start DRP
'''

import argparse
import yaml
from datetime import datetime, timedelta
from urllib.request import urlopen
import json
from pathlib import Path
import os
import sys
import subprocess
import psutil
import getpass


def main():
    args = parse_args()

    # Get input parameters
    inst = args.instrument.upper()
    command = args.command
    utdate = args.utdate

    skip_avail = args.skip_avail

    # Go to the directory of the source
    dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir)

    # Read configuration file and verify
    with open('drp_config.live.ini') as f: config = yaml.safe_load(f)
    verify_inputs(config, inst)

    koa_dir, drp_dir = get_dirs(config, inst, utdate, args.level)

    # DRP name and command
    drp = config[inst]['DRP']
    drp_cmd, extras = get_cmd(config, inst, koa_dir, args.level)

    # Do the request
    pid = is_drp_running(drp, extras, utdate)
    if command == 'stop':
        pid = process_stop(pid)
    elif command == 'start':
        process_start(pid, drp, drp_dir, drp_cmd, config, inst, utdate, skip_avail)
        pid = is_drp_running(drp, extras, utdate)
    elif command == 'restart':
        pid = process_stop(pid)
        process_start(pid, drp, drp_dir, drp_cmd, config, inst, utdate, skip_avail)

    exit(0) if len(pid) > 0 else exit(1)


def parse_args():
    utdate = datetime.utcnow().strftime('%Y%m%d')

    # Define input parameters
    parser = argparse.ArgumentParser(description='drp_manager.py input parameters')

    parser.add_argument('instrument', type=str, help='Instrument name')
    parser.add_argument('command', type=str,
                        choices=['start', 'stop', 'restart', 'status'],
                        help='start, stop, restart, status', default='start')
    parser.add_argument('--level', type=int, default=1, choices=[1, 2],
                        help='level to process: 1 or 2')
    parser.add_argument('--utdate', type=valid_date, default=utdate,
                        help='UT date for DRP process (yyyymmdd)')
    parser.add_argument('--skip_avail', action='store_true',
                        help='Override schedule check')

    return parser.parse_args()


def is_drp_running(drp, extras, utdate):
    '''
    Returns PID if DRP is currently running, else 0
    '''
    matches = []
    current_user = getpass.getuser()
    list1 = [drp, utdate]

    for proc in psutil.process_iter():
        pinfo = proc.as_dict(attrs=['name', 'username', 'pid', 'cmdline'])

        if pinfo['username'] != current_user:
            continue

        found = 0
        for name in list1:
            for cmd in pinfo['cmdline']:
                if name in cmd:
                    found += 1

        if found >= len(list1):
            matches.append(pinfo)

        for cmd in pinfo['cmdline']:
            for e in extras:
                if e in cmd:
                    matches.append(pinfo)
                    continue

    if len(matches) == 0:
        print("WARN: NO MATCHING PROCESSES FOUND")
        return []
    elif len(matches) > 1:
        print(f"WARN: MULTIPLE MATCHES: \n {matches}")
    else:
        print(f"FOUND PROCESS: {matches[0]}")

    return matches


def process_start(pid, drp, drp_dir, drp_cmd, config, inst, utdate, skip_avail):
    '''
    Start the requested DRP
    '''
    if len(pid) > 0:
        print('{drp} already running with PID: {pid}')
        return

    # start the DRP
    cmd = []
    for word in drp_cmd.split(' '):
        cmd.append(word)

    print(f'Starting "{drp}" with the cmd:' + str(cmd))
    try:
        # Verify instrument is available
        if not skip_avail:
            hst = datetime.strptime(utdate, '%Y%m%d') - timedelta(days=1)
            hstDate = hst.strftime('%Y-%m-%d')
            api = f"{config['API']['TEL']}cmd=getInstrumentStatus&date={hstDate}"
            data = urlopen(api)
            data = data.read().decode('utf8')
            data = json.loads(data)
            if data[0][inst]['Available'] == 0:
                print(f"{inst} is not available")
                return

            print(f"{inst} is available")

        # change to output directory and start DRP
        os.chdir(drp_dir)
        p = subprocess.Popen(cmd)
    except Exception as e:
        print('Error running command: ' + str(e))
    print('Done')


def process_stop(pid):
    '''
    Use psutil to kill the process ID
    '''

    if len(pid) == 0:
        print('Process is not running')
    else:
        for entry in pid:
            print('Killing PID', entry['pid'])
            p = psutil.Process(entry['pid'])
            p.terminate()
        pid = []

    return pid


def verify_inputs(config, inst):

    try:
        config[inst]
    except:
        sys.exit('Unknown inst')

    if config[inst]['ACCOUNT'] != getpass.getuser():
        sys.exit('Invalid account')

    return True


def valid_date(s):
    try:
        datetime.strptime(s, "%Y%m%d")
        return s
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def get_dirs(config, inst, utdate, level):

    # Directory to find KOA data
    koa_dir = f"{config['KOA']['DIR']}/{inst}/{utdate}/lev0"
    if not os.path.isdir(koa_dir):
        sys.exit(f"{koa_dir} does not exist")

    # Directory to write DRP data
    drp_dir = f"{config[inst]['DRPDIR']}/{utdate}/lev{level}"
    if not os.path.isdir(drp_dir):
        try:
            Path(drp_dir).mkdir(parents=True, exist_ok=True)
        except:
            sys.exit(f"{drp_dir} does not exist")

    return koa_dir, drp_dir


def get_cmd(config, inst, koa_dir, level):
    drp_config = config[inst][f'CONFIG_LEV{level}']
    drp_cmd = config[inst][f'COMMAND_LEV{level}']
    drp_cmd = drp_cmd.replace('DIRECTORY', koa_dir)
    drp_cmd = drp_cmd.replace('DRP_CONFIG', drp_config)
    extras = config[inst]['EXTRAS']

    return drp_cmd, extras


if __name__ == "__main__":
    main()

