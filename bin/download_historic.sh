#!/bin/bash
for yr in {1983..2021}
do
    wget "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p05/chirps-v2.0.$yr.days_p05.nc"
    gsutil mv "chirps-v2.0.$yr.days_p05.nc" <some-cloud-address>
done
