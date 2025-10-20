#!/bin/bash
#
# Meraki Chart Generation Script
# Generates charts from historical database data
#

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Generate charts using all historical data
python main.py --use-historical --generate-charts --weeks 52 --months 12

# Exit with the Python script's exit code
exit $?
