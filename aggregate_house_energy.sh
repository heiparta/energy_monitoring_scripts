#!/bin/bash
set -euo pipefail

START_YEAR=2017
END_YEAR=$(date +%Y)

# Calculate monthly sums
for year in $(seq $START_YEAR $END_YEAR); do
	for month in $(seq 1 12); do
		influx -database house_energy -execute "select last(kwh) as kwh into house_energy_by_month \
			from (select cumulative_sum(kwh) as kwh from house_energy \
			where year='"$year"' and month='"$month"')"
	done
done

# Calculate yearly sums
for year in $(seq $START_YEAR $END_YEAR); do
	influx -database house_energy -execute "select last(kwh) as kwh into house_energy_by_year from \
		(select cumulative_sum(kwh) as kwh from house_energy where year='"$year"')"
done
