
# Energy monitoring scripts

1. Download yearly consumption excel data (manually)
1. Convert .xlsx data into .csv files, one per metric (conversion.py)
1. Insert the data into influxdb using telegraf (telegraf_file.conf)
1. Calculate aggregations (aggregate_house_energy.sh)

# Preparations

    python3 -m virtualenv venv --python=$(which python3)
    python3 ./conversion.py kulutustiedot_2463453700_2017.xlsx -o file_kwh_2017.csv house_energy -t xlsx

