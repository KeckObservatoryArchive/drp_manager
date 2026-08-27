# drp_manager

Scripts to manage starting and stopping DRPs used to archive level 1 (quick-look) and level 2 (science-ready) data products.

After installation, the following files need to be edited:

drp_manager.sh: Insert the PATH and path to the drp_manager.py
drp_config.ini: set all of the required information
kcwi_scripts/kcwi.ini: Set cmd_path to the path to start_kcwi.py, and the RTI information
