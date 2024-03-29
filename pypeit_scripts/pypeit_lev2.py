from copy import copy
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
#### Bad Deimos detector. Temporary until this stops changing all the time.
###

deimos_det_5_is_bad = True
deimos_detnum = "1,(2,6),(3,7),(4,8)"

###
##### PypeIt Stuff
###


def generate_pypeit_files(pargs, setup, cfg):   
    """Creates the a .pypeit file for every configuration identified in the
    input files

    Parameters
    ----------
    pargs : Parsed command line arguments
        Should be the output from get_parsed_args()
    """     

    setup_dir = os.path.join(pargs.output, "pypeit_files")
    root = os.path.join(pargs.input, pargs.root)

    print(f'Looking for files matching {root}*.fits*')
    print(f'Outputs will be saved in {setup_dir}')

    # Create the setup object
    ps = setup.from_file_root(root, pargs.pypeit_name,
                                    extension=".fits")
    ps.user_cfg = ['[rdx]', 'ignore_bad_headers = True']
    if "deimos" in pargs.inst and deimos_det_5_is_bad:
        ps.user_cfg += [f'detnum = {deimos_detnum}']

    # If the instrument is IR, use the -b flag (write_bkg_pairs=True)
    ir_insts = cfg['INSTRUMENTS']['ir_insts'].split(' ')
    is_ir = False
    if pargs.inst in ir_insts:
        print("Instrument is IR, using background pairs")
        is_ir = True

    # Run the setup
    ps.run(setup_only=True, calibration_check=False, sort_dir=setup_dir,
           obslog=True, write_bkg_pairs=is_ir)

    # Save the setup to .pypeit files
    # ps.fitstbl.write_pypeit(setup_dir, configs='all', write_bkg_pairs=is_ir)
    pypeit_files = ps.fitstbl.write_pypeit(output_path=setup_dir,
                                           write_bkg_pairs=is_ir,
                                           configs='all',
                                           version_override=None,
                                           date_override=None)

def run_pypeit_helper(pypeit_file, pargs, cfg):
    """Runs a PypeIt reduction off of a specific .pypeit file, using the io
    parameters in pargs.

    The reduction is launched in a subprocess using the subprocess library, with
    stdout and stderr directed to a single log file. 

    Parameters
    ----------
    pypeit_file : str or pathlike
        .pypeit file to reduce
    pargs : Parsed command line arguments
        Should be from get_parsed_args()
    """

    print(f"Processing config from {str(pypeit_file)}")

    # Open file to dump logs into
    logname = os.path.splitext(pypeit_file)[0] + '.log'
    logpath = os.path.join(pargs.output, logname)
    f = open(logpath, 'w+')
    
    # Get full output path
    outputs = os.path.join(pargs.output, os.path.splitext(pypeit_file)[0])
    
    # Run the reduction in a subprocess
    args = ['run_pypeit']
    args += [pypeit_file]
    args += ['-r', str(outputs)]
    args += ['-o']

    if pargs.calib == True:
        args += ['-c']

    proc = subprocess.run(args, stdout=f, stderr=f)

    if proc.returncode != 0:
        print(f"Error encountered while reducing {pypeit_file}")
        print("Attempting to alert RTI anyway...")
    else:
        print(f"Reduced {pypeit_file}")
        print("Alerting RTI...")
    
    alert_RTI(outputs, pargs, cfg)
    print(f"Log can be found at {logpath}")
    f.close()


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

    parser.add_argument('inst', help='Instrument choice. ' + 
                        'To see availble instruments, use --instrument-options')

    parser.add_argument('-i', '--input-dir', dest='input', 
                        default=default_input,
                        help='Path to raw files. Defaults to current directory')
    
    parser.add_argument('-o', '--output-dir', dest='output',
                        default=default_output,
                        help='Directory to put output in. Defaults to ./redux')
    
    parser.add_argument('-r', '--root', dest='root',
                        help='Base root of the files. E.g. "DE.", "KB.",' + 
                        ' "kb". If none, will attempt to find a suitable root' +
                        'from the config.')
    
    parser.add_argument('-n', '--num-proc', dest='num_proc', type=int,
                        help='number of processes to launch')
    
    parser.add_argument('-c', '--config', dest='cfg_file',
                        default='./pypeit_lev2.live.ini', help='Config file to use')
    
    parser.add_argument('--setup-only', dest='setup', action='store_true',
                        help="Only create the pypeit files, don't reduce them")
    
    parser.add_argument('--instrument-options', dest='opts',
                        action='store_true',
                        help='prints the instruments this script can reduce')
    
    parser.add_argument('--calibonly', dest='calib', action='store_true',
                        help='process calibrations only')
    
    pargs =  parser.parse_args()

    return pargs

def print_inst_options(cfg):
    inst_options = "', ".join(cfg.inst_opts.keys())
    print(f"Options are: '{inst_options}'")

def main():

    try:
        from pypeit.pypeitsetup import PypeItSetup
    except ImportError:
        print("Could not import PypeIt. Is it installed in this environment?")
        print("Exiting...")
        sys.exit(1)

    
    # Parse the arguments
    pargs = get_parsed_args()
    
    # Get configuration
    cfg = get_config(pargs.cfg_file)

    if pargs.opts:
        print_inst_options(cfg)
        sys.exit(0)

    # Check if the input instrument name is valid
    if pargs.inst not in cfg.inst_opts.keys():
        print("Invalid instrument name")
        print_inst_options(cfg)
        sys.exit(0)
    
    # Get PypeIt's instrument name
    pargs.pypeit_name = cfg.inst_opts[pargs.inst]['pypeit_name']

    # If no root is specified, get it from the instruments list
    if pargs.root is None:
        pargs.root = cfg.inst_opts[pargs.inst]['root']


    # Create all the pypeit files
    generate_pypeit_files(pargs, PypeItSetup, cfg)
    
    setup_files = Path(pargs.output) / 'pypeit_files'
    # Select only the pypeit files that are for an instrument configuration
    pypeit_files = list(setup_files.rglob(f'{pargs.pypeit_name}_?.pypeit'))
    
    # Add in special parameters
    # For each pypeit file
        # Open it
        # Advance to user parameters
        # Add in whatever we require
        # Close and save
    
    pars = "[calibrations]\n[[flatfield]]\nsaturated_slits = mask\n"
    
    for file in pypeit_files:
        with open(file, 'r+') as f:
            contents = f.readlines()
            for index, line in enumerate(contents):
                if "# Setup" in line:
                    contents.insert(index - 1, pars)
                    break
            f.seek(0)
            f.writelines(contents)
            
    args = []

    # Create the arguments for the pool mapping function
    print("Found the following .pypeit files:")
    for f in pypeit_files:
        print(f'    {f}')
        new_pargs = copy(pargs)
        # new_pargs.output = os.path.join(pargs.output)
        print(f"          Output is {new_pargs.output}")
        args.append((f, new_pargs, cfg))

    if not pargs.setup:
        num = pargs.num_proc if pargs.num_proc else os.cpu_count() - 1
        print(f"Launching {num} procs to reduce {len(pypeit_files)} configs")

        with Pool(processes=num) as pool:
            pool.starmap(func=run_pypeit_helper, iterable=args)
    
        print("Reduction complete!")

if __name__ == '__main__':
    main()
