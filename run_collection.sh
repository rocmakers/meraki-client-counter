#!/bin/bash
#
# Meraki Client Collection Script
# Runs daily to collect and store client data
#

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the collection (stores data in database)
python main.py --verbose

# Exit with the Python script's exit code
exit $?
