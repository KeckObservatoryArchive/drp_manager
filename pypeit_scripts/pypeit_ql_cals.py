# Run the normal PypeIt Setup
# Add the QL specific parameters to the pypeit file
# Make 3 copies, totaling 4
# For each, add the appropriate mosaic parameter
# Execute PypeIt on the 4 files in parallel

import sys
from pathlib import Path
import subprocess
import os

from pypeit.scripts.setup import Setup

# Run the normal PypeIt Setup:

spectrograph = sys.argv[1]
file_root = sys.argv[2]

QL_lines = [
"detnum\n"
"quicklook = True\n",
"[baseprocess]\n",
"use_specillum = False\n",
"use_pattern = False\n",
"use_darkimage = False\n",
"[calibrations]\n",
"[[flatfield]]\n",
"slit_illum_finecorr = False\n"
]
mscs = ["1", "(2,6)", "(3,7)", "(4,8)"]

Setup.main(Setup.parse_args(['-s', spectrograph, '-r', file_root, '-c', 'all']))

# for each setup, edit the pypeit file
# Each setup is in a directory that looks like "[spectrograph]_[A]"
# Get the path to the setup files

setup_dirs = Path.glob(Path.cwd(), f"{spectrograph}_*")

# Loop over the directories
for setup_dir in setup_dirs:
    # Get the path to the pypeit file
    pypeit_file = list(Path.glob(setup_dir, "*.pypeit"))[0]
    # Read the pypeit file
    
    print(f"Opening {pypeit_file}")
    with open(pypeit_file, 'r') as f:
        lines = f.readlines()

        # Edit the pypeit file
        for i, line in enumerate(lines):
            if line.startswith("[rdx]"):
                lines[i+2:i+2] = QL_lines
                break
    
    with open(pypeit_file, 'w') as f:
        # Write the lines back to the file
        f.writelines(lines)
    if 'deimos' in spectrograph.lower():
        for j, msc in enumerate(mscs):
            new_file = pypeit_file.parent / (pypeit_file.stem + f"_{j}.pypeit")
            print(f"new file: {new_file}")
            with open(pypeit_file, 'r') as f:
                lines = f.readlines()

                # Edit the pypeit file
                for i, line in enumerate(lines):
                    if line.startswith("detnum"):
                        lines[i] = f"detnum = {msc}\n"
                        break
            with open(new_file, 'w') as g:
                # Write the lines back to the file
                g.writelines(lines)
            
        # Remove the original file
        pypeit_file.unlink()

# Now run the pypeit files in parallel
# Get the list of pypeit files
pypeit_files = list(Path.rglob(Path.cwd(), "*.pypeit"))
# starmap over the list of pypeit files
from multiprocessing import Pool



def run_pypeit_helper(pypeit_file):
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
    logpath = os.path.splitext(pypeit_file)[0] + '.log'
    # logpath = os.path.join(pargs.output, logname)
    f = open(logpath, 'w+')

    # Get full output path
    #outputs = os.path.join(pargs.output, os.path.splitext(pypeit_file)[0])
    outputs = os.path.splitext(pypeit_file)[0]
    # Run the reduction in a subprocess
    args = ['run_pypeit']
    args += [pypeit_file]
    args += ['-o']
    args += ['-c']
    args += ['-r']
    args += [Path(pypeit_file).parent]

    proc = subprocess.run(args, stdout=f, stderr=f)

    if proc.returncode != 0:
        print(f"Error encountered while reducing {pypeit_file}")
        print("Attempting to alert RTI anyway...")
    else:
        print(f"Reduced {pypeit_file}")
    
    f.close()

with Pool(processes=25) as pool:
    pool.map(run_pypeit_helper, pypeit_files)
