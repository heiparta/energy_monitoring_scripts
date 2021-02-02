#!/bin/bash
set -euo pipefail
YEAR="$(date +%Y)"

set +u
source venv/bin/activate
set -u

echo "Downloading data for past week"
./hsotool.py --config hsotool_config.yaml

echo "Converting xlsx data to csv"
./conversion.py $PWD/data_current.xlsx -o file_kwh_current.csv house_energy -t xlsx
./conversion.py $PWD/data_current.xlsx -o file_temp_current.csv outside_temperature -t xlsx

echo "Inserting data to InfluxDB"
sudo docker run --rm -v $PWD:/input telegraf  --config /input/telegraf_file.conf --once

echo "Generating aggregations"

echo "Calculating aggregate statistics"
./aggregate_house_energy.sh

echo "All done."


