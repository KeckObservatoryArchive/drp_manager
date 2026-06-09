import os
import sys
import requests
from copy import copy
from datetime import datetime
from pathlib import Path
from multiprocessing import Pool
from argparse import ArgumentParser
import subprocess

import yaml
import numpy as np

try:
    from pypeit.pypeitsetup import PypeItSetup
    from pypeit.spectrographs.util import load_spectrograph
except ImportError:
    print("Could not import PypeIt. Is it installed in this environment?")
    print("Exiting...")
    sys.exit(1)

###
##### PypeIt Stuff
###

def build_setup_object(pargs, root, cfg_lines):
    # This is a combination of PypeItSetup.from_file_root and from_rawfiles
    spec = load_spectrograph(pargs.pypeit_name).__class__
    files = spec.find_raw_files(root, extension=".fits")
    nfiles = len(files)
    if nfiles == 0:
        print(f'Unable to find any raw files for {spec.name} in {root}!')
    else:
        print(f'Found {nfiles} {spec.name} raw files.')
        
    cfg_lines = ['[rdx]', f'    spectrograph = {pargs.pypeit_name}'] + cfg_lines

    # Instantiate
    return PypeItSetup(files, cfg_lines=cfg_lines)

def generate_pypeit_files(pargs, setup, cfg):   
    """Creates the a .pypeit file for every configuration identified in the
    input files

    Parameters
    ----------
    pargs : Parsed command line arguments
        Should be the output from get_parsed_args()
    """     

    setup_dir = Path(pargs.output).absolute() / "pypeit_files"
    if not setup_dir.exists():
        setup_dir.mkdir(parents=True)
    root = Path(pargs.input) / pargs.root
    root = str(root)

    print(f'Looking for files matching {root}*.fits*')
    print(f'Outputs will be saved in {setup_dir}')

    # Create the setup object
    # ps = setup.from_file_root(root, pargs.pypeit_name,
    #                                 extension=".fits")
    inst_config = Path(__file__).parent / 'instrument_configs' / f'{str(pargs.inst).lower()}.yaml'

    if inst_config.exists():
        print(f"Applying instrument-specific configuration from {inst_config}")
        with open(inst_config) as f:
            cfg_inst = yaml.safe_load(f)
            if 'user_cfg' in cfg_inst:
                lines = get_user_lines_from_dict(cfg_inst['user_cfg'], lines=[])
    ps = build_setup_object(pargs, root, cfg_lines=lines if lines else [])

    # Run the setup
    ps.run(setup_only = True, clean_config = True)

    # If the instrument is IR, use the -b flag (write_bkg_pairs=True)
    is_ir = cfg['INSTRUMENTS'][pargs.inst]['ir']

    # Handle any instrument-specific configuration
    inst_config = Path(__file__).parent / 'instrument_configs' / f'{str(pargs.inst).lower()}.yaml'
    # if inst_config.exists():
    #     print(f"Applying instrument-specific configuration from {inst_config}")
    #     with open(inst_config) as f:
    #         cfg_inst = yaml.safe_load(f)
    #     handle_instrument_config(cfg_inst, ps)
    # else:
    #     print(f"No instrument-specific configuration found for {pargs.inst} at {inst_config}")
    #     print("Exiting...")
    #     sys.exit(1)


    # Save the setup to .pypeit files
    pypeit_files = ps.fitstbl.write_pypeit(output_path=setup_dir,
                                           cfg_lines=ps.user_cfg,
                                           write_bkg_pairs=is_ir,
                                           configs='all',
                                           version_override=None,
                                           date_override=None)
    
    ps.fitstbl.write_sorted(setup_dir / f"{pargs.inst}.sorted", write_bkg_pairs=is_ir)


    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # The following is commented out until we have a need for it. If this     #
    # script is used to process different sets of data with the same          # 
    # spectrograph, the config names will collide.                            #
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    
    # If we're using LRIS, add a "B" or "R" to the config name
    # if 'lris' in pargs.pypeit_name:
    #     if len(pypeit_files) > 26:
    #         print("Unable to parse configuration names for more than 26 LRIS configs")
    #         print("Exiting...")
    #         sys.exit(1)
    #     # Get the red/blue prefix:
    #     prefix = "B" if 'blue' in pargs.pypeit_name else "R"
    #     print(f"Renaming LRIS configs to include {prefix} prefix")
    #     Each entry looks like /path/to/output/keck_lris_A/keck_lris_A.pypeit
    #     for pypeit_file_name in pypeit_files:
    #         config_name = pypeit_file_name.split('.pypeit')[0][-1]
    #         pypeit_file = Path(pypeit_file_name)
    #         new_file_path = pypeit_file.parent.parent / f"{pargs.pypeit_name}_{prefix}{config_name}" / f"{pargs.pypeit_name}_{prefix}{config_name}.pypeit"
    #         # Move the file to the new location
    #         new_file_path.parent.mkdir(parents=True, exist_ok=True)
    #         pypeit_file.rename(new_file_path)
    #         print(f"Renamed {pypeit_file} to {new_file_path}")

def handle_instrument_config(cfg, ps):
    """Adds user parameters from the config file to the PypeItSetup object.
    This modifies the PypeItSetup object in place.

    Parameters
    ----------
    cfg : ConfigParser
        The configuration file parser object.
    ps : PypeItSetup
        The PypeItSetup object to modify.
    """

    # If there are any allowed keywords, keep only those files in the table
    if 'allowed_keywords' in cfg:

        # Create a total mask to keep track of which rows to keep (all False to start)
        total_mask = np.zeros(len(ps.fitstbl), dtype=bool)
        
        for key in cfg['allowed_keywords']:
            allowed_values = cfg['allowed_keywords'][key].split(',')
            # create a mask to store which rows to keep
            for value in allowed_values:
                # Where the a column value matches the allowed value, keep it
                mask = ps.fitstbl[key] == value
                if mask.any():
                    # Update the total mask
                    total_mask |= mask
        
        print("Removing the following files:")
        for i, row in enumerate(ps.fitstbl):
            if not total_mask[i]:
                print(f"    {row['filename']} because {key} = {row[key]}")
        
        # Apply the total mask to the fitstbl
        ps.fitstbl = ps.fitstbl[total_mask]
        if len(ps.fitstbl) == 0:
            print("No files left after applying allowed_keywords. Exiting...")
            sys.exit(1)

    # Add any user parameters from the config file
    if 'user_cfg' in cfg:
        lines = get_user_lines_from_dict(cfg['user_cfg'], lines=[])
        ps.append_user_cfg(lines)

    # If there are thresholds to apply, do that here
    if 'fits_table_thresholds' in cfg:
        for key in cfg['fits_table_thresholds']:
            difference = float(cfg['fits_table_thresholds'][key])
            print(f"Combining like values in {key} within {difference}")
            combine_like_values(ps.fitstbl, key, difference)


def get_user_lines_from_dict(cfg_dict, lines = [], bracket_level=1):
    """Converts a dictionary of configuration parameters into a list of strings
    that can be added to a PypeItSetup object. This is done recursively to
    handle nested dictionaries.

    The rdx section is handled specially, as it is always present at the top
    level of the user_cfg section and we don't want to duplicate it.

    Parameters
    ----------
    cfg_dict : dict
        The dictionary of configuration parameters.
    lines : list, optional
        The list of strings to append to. Default is an empty list.
    bracket_level : int, optional
        The current level of brackets to use. Default is 1.
    """

    for key in cfg_dict:

        # Handle rdx section specially
        if key == 'rdx':
            # For each key in the rdx section, add it to the lines immediately
            for rdx_key in cfg_dict['rdx']:
                line = f"{rdx_key} = {cfg_dict['rdx'][rdx_key]}"
                lines.append(line)
            continue

        # If the value is a dictionary, recurse
        if isinstance(cfg_dict[key], dict):
            pre_brackets = '[' * bracket_level
            post_brackets = ']' * bracket_level
            lines.append(f"{pre_brackets}{key}{post_brackets}")
            get_user_lines_from_dict(cfg_dict[key], lines, bracket_level + 1)
        # If the value isn't a dictionary, it's a parameter, so add it
        else:
            line = f"{key} = {cfg_dict[key]}"
            lines.append(line)

    return lines


def combine_like_values(tbl, colname, difference):
    """Combines values in a table column that should be considered the same.
    For example, if the column is a dispersion angle, and two values are within
    `difference`, they should be considered the same. This requires the sorting
    of the table by the column first.
    
    This function modifies the table in place.

    Parameters
    ----------
    tbl : PypeItMetaData
        The input table containing the data to be combined.
    colname : str
        The name of the column to be processed.
    difference : float
        The maximum difference between values to be considered the same. 
    """

    tbl.sort(colname)

    for i, value in enumerate(tbl[colname]):
        # Skip the first one, as there's no previous value to compare to
        if i == 0:
            continue
        # If the value is within difference of the previous value, set it to the previous value
        if abs(value - tbl[colname][i - 1]) < difference:
            tbl[colname][i] = tbl[colname][i - 1]


def run_pypeit_helper(pypeit_file, pargs, cfg):
    """Runs a PypeIt reduction off of a specific .pypeit file, using the io
    parameters in pargs.

    The reduction is launched in a subprocess using the subprocess library, with
    stdout and stderr directed to a single log file.

    This should ultimately be changed to invoke PypeIt directly, as argument
    injection is a security risk.

    Parameters
    ----------
    pypeit_file : str or pathlike
        .pypeit file to reduce
    pargs : Parsed command line arguments
        Should be from get_parsed_args()
    """

    print(f"Processing config from {str(pypeit_file)}")

    # Open file to dump logs into
    logpath = os.path.splitext(pypeit_file)[0] + '.log'
    f = open(logpath, 'w+')
    
    # Get full output path
    outputs = os.path.splitext(pypeit_file)[0]

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
    """Alerts the RTI system that a directory is ready for ingestion.

    Parameters
    ----------
    directory : str
        The directory that is ready for ingestion.
    pargs : Namespace
        The parsed command line arguments.
    cfg : dict
        The configuration dictionary.
    
    Returns
    -------
    response : requests.Response or None
        The response from the RTI server, or None if there was an error.
    """

    def get_url(url, data):
        try:
            res = requests.get(url,
                               params = data, 
                               auth = (cfg['RTI']['user'], cfg['RTI']['pass']))
            print(f"Sent {res.request.url}")
            print(f"Response:\n{res.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error caught while posting to {url}:")
            print(e)
            print("Continuing without alerting RTI")
            return None
        return res
    
    print(f"Alerting RTI that {directory} is ready for ingestion")
    url = cfg['RTI']['url']

    data = {
        'instrument': pargs.inst,
        'ingesttype': cfg['RTI']['rti_ingesttype'],
        'datadir': str(directory),
        'start': str(cfg['start_time']),
        'reingest': cfg['RTI']['rti_reingest'],
        'testonly': cfg['RTI']['rti_testonly'],
        'dev': cfg['RTI']['rti_dev']
    }
    
    #print({section: dict(cfg[section]) for section in cfg.sections()})
    res = get_url(url, data)
    

###
##### Script Stuff
###

def get_config(cfg_file):
    """Reads in the configuration file and returns a dictionary of the
    configuration parameters.
    Parameters
    ----------
    cfg_file : str or pathlike
        The path to the configuration file.
    
    Returns
    -------
    cfg : dict
        The configuration parameters.
    """

    with open(cfg_file) as f:
            cfg = yaml.safe_load(f)

    cfg['start_time'] = datetime.utcnow()

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

    parser.add_argument('inst', default="", help='Instrument choice. ' + 
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
                        default='./pypeit_lev2.live.yaml', help='Config file to use')
    
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
    """Prints the available instrument options from the configuration file.
    Parameters
    ----------
    cfg : dict
        The configuration parameters.
    """
    
    inst_options = "', ".join(cfg['INSTRUMENTS'].keys())
    print(f"Options are: '{inst_options}'")

def main():
    
    # Parse the arguments
    pargs = get_parsed_args()
    
    # Get configuration
    cfg = get_config(pargs.cfg_file)

    if pargs.opts or pargs.inst == "":
        print_inst_options(cfg)
        sys.exit(0)

    # Check if the input instrument name is valid
    if pargs.inst not in cfg['INSTRUMENTS'].keys():
        print("Invalid instrument name")
        print_inst_options(cfg)
        sys.exit(0)
    
    # Get PypeIt's instrument name
    pypeit_name = cfg['INSTRUMENTS'][pargs.inst]['pypeit_name']

    # If no root is specified, get it from the instruments list
    if pargs.root is None:
        pargs.root = cfg['INSTRUMENTS'][pargs.inst]['root']

    roots = pargs.root if isinstance(pargs.root, list) else [pargs.root]

    # If we're using a multi-arm instrument (i.e. LRIS, although some day maybe
    # pypeit KCWI/KCRM), we need to reduce the red and blue sides separately, 
    # so we need to make pypeit_name a list
    if not isinstance(pypeit_name, list):
        pypeit_name = [pypeit_name]
    
    if not isinstance(pargs.root, list):
        roots = [pargs.root]

    for i, spectrograph_name in enumerate(pypeit_name):
        pargs.pypeit_name = spectrograph_name
        pargs.root = roots[i]
        # Create all the pypeit files
        generate_pypeit_files(pargs, PypeItSetup, cfg)
    
    setup_files = Path(pargs.output) / 'pypeit_files'

    # Select only the pypeit files that are for an instrument configuration
    pypeit_files = list(setup_files.rglob(f'keck_*.pypeit'))
            
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
    
    print(f"Finished reductions at {datetime.now()} HST")

if __name__ == '__main__':
    main()
