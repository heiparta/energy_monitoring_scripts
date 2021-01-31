#!/bin/bash
set -euo pipefail
YEAR="$(date +%Y)"

set +u
source venv/bin/activate
set -u

echo "Downloading data for year $YEAR"
./hsotool.py --config hsotool_config.yaml $YEAR

echo "Converting xlsx data to csv"
./conversion.py $PWD/data_$YEAR.xlsx -o file_kwh_$YEAR.csv house_energy -t xlsx
./conversion.py $PWD/data_$YEAR.xlsx -o file_temp_$YEAR.csv outside_temperature -t xlsx

echo "Inserting data to InfluxDB"
sudo docker run --rm -v $PWD:/input telegraf  --config /input/telegraf_file.conf --once

echo "Generating aggregations"

echo "Calculating aggregate statistics"
./aggregate_house_energy.sh

echo "All done."


