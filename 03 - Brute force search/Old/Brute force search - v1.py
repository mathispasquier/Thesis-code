# -*- coding: utf-8 -*-
"""
Created on Mon Feb  5 16:14:05 2024

@author: mpa
"""

import csv

import pvlib

import pandas as pd

import matplotlib.pyplot as plt

import numpy as np

from math import cos, sin, atan, atan2, radians, degrees

""" Input parameters"""

tz='Etc/GMT-1'
latitude = 55.696166
longitude = 12.105216
name = 'Risoe'
axis_tilt=0
axis_azimuth=180
max_angle=55
altitude = 14.5
GCR = 0.28

""" Get weather data (real data from .csv file) 
Time, GHI, DHI, DNI, Solar zenith, Solar azimuth
From 2021-01-01 to 2021-12-31 approximately every 20sec (not regular)  """

real_weather = pd.read_csv('../../Risø Data formatted.csv')

# Set the index with the format Datetime

real_weather.index = pd.date_range('2021-01-01', '2022-01-01', freq='1min', tz=tz)
real_weather = real_weather.drop(['TmStamp'],axis=1)

# Select the days

""" Select the days when to calculate via brute force search """

begin = '2021-06-01 00:00:00+01:00'
end = '2021-06-02 00:00:00+01:00'

real_weather = real_weather.loc[begin:end]

""" Calculate the solar position for each time """

solpos = pvlib.solarposition.get_solarposition(real_weather.index, latitude, longitude, altitude)

apparent_zenith = solpos["apparent_zenith"]
zenith = solpos["zenith"]
azimuth = solpos["azimuth"]

""" Calculate air mass and DNI extra for the Perez transposition model """

real_weather["DNI_extra"] = pvlib.irradiance.get_extra_radiation(real_weather.index)
real_weather["air_mass"] = pvlib.atmosphere.get_relative_airmass(zenith)

GHI = real_weather["GHI"]
DHI = real_weather["DHI"]
DNI = real_weather["DNI"]
DNI_extra = real_weather["DNI_extra"]
air_mass = real_weather["air_mass"]


""" For each time, calculate optimal angle of rotation (with 2° resolution) that yields the maximum POA
Use a transposition model to calculate POA irradiance from GHI, DNI and DHI """

brute_force_search = pd.DataFrame(data=None, index=real_weather.index)
brute_force_search["beta_opt"] = 0.0
brute_force_search["POA_global_opt"] = 0.0

beta_range = range(-max_angle, max_angle, 2)

for time, data in real_weather.iterrows():
    
    POA_max = 0
    beta_POA_max = 0
    
    for beta in beta_range:
    
        # Transposition model 
        
        POA_data = pvlib.irradiance.get_total_irradiance(beta, axis_azimuth, zenith[time], azimuth[time], DNI[time], GHI[time], DHI[time], DNI_extra[time], air_mass[time], model='perez')
        POA_global = POA_data["poa_global"]
        
        # Definition of the new optimal angle when the associated POA is maximal
        
        if POA_global > POA_max:
            
            POA_max = POA_global
            beta_POA_max = beta
    
    brute_force_search.loc[time,"beta_opt"] = beta_POA_max
    brute_force_search.loc[time,"POA_global_opt"] = POA_max
        
""" Comparison with true tracking """

truetracking_angles = pvlib.tracking.singleaxis(
    apparent_zenith=apparent_zenith,
    apparent_azimuth=azimuth,
    axis_tilt=axis_tilt,
    axis_azimuth=axis_azimuth,
    max_angle=max_angle,
    backtrack=False,  # for true-tracking
    gcr=GCR)  # irrelevant for true-tracking

truetracking_position = truetracking_angles['tracker_theta'].fillna(0)

""" Plot data """

fig, axes = plt.subplots(nrows=2, ncols=1, sharex=True)

brute_force_search["beta_opt"].plot(title='Tracking Curve', label="Optimal tracking", ax=axes[0])
truetracking_position.plot(title='Tracking Curve', label="Astronomical tracking",ax=axes[0])
#optimal_angle.index = truetracking_position.index

GHI.plot(title='Irradiance', label="GHI", ax=axes[1])
DHI.plot(title='Irradiance', label="DHI", ax=axes[1])
DNI.plot(title='Irradiance', label="DNI", ax=axes[1])

axes[0].legend(title="Tracker Tilt")
axes[1].legend(title="Irradiance")


plt.legend()
plt.show() 
    
    