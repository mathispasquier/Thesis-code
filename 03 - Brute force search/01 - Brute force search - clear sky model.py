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

real_weather = pd.DataFrame(data=None, index=pd.date_range('2021-01-01', '2022-01-01', freq='1min', tz=tz))

# Select the days

""" Select the days when to calculate via brute force search """

#begin = '2021-06-01 10:00:00+01:00'
#end = '2021-06-01 10:01:00+01:00'

begin = '2021-06-01 00:00:00'
end = '2021-06-02 00:00:00'

real_weather = real_weather.loc[begin:end]

""" Calculate the solar position for each time """

solpos = pvlib.solarposition.get_solarposition(real_weather.index, latitude, longitude, altitude)

apparent_zenith = solpos["apparent_zenith"]
zenith = solpos["zenith"]
azimuth = solpos["azimuth"]

""" Calculate air mass and DNI extra for the Perez transposition model """

real_weather["DNI_extra"] = pvlib.irradiance.get_extra_radiation(real_weather.index)
real_weather["airmass"] = pvlib.atmosphere.get_relative_airmass(zenith)

DNI_extra = real_weather["DNI_extra"]
airmass = real_weather["airmass"]

linketurbidity = pvlib.clearsky.lookup_linke_turbidity(real_weather.index, latitude, longitude)
clearsky = pvlib.clearsky.ineichen(apparent_zenith, airmass, linketurbidity, altitude)

real_weather["GHI"] = clearsky['ghi']
real_weather["DHI"] = clearsky['dhi']
real_weather["DNI"] = clearsky['dni']

GHI = clearsky['ghi']
DHI = clearsky['dhi']
DNI = clearsky['dni']

""" For each time, calculate optimal angle of rotation (with 2° resolution) that yields the maximum POA
Use a transposition model to calculate POA irradiance from GHI, DNI and DHI """

def find_optimal_rotation_angle(ghi, dhi, dni, dni_extra, airmass, solar_position):
    """
    Find the optimal rotation angle within given limits.
    """
    diffuse_tracking = pd.DataFrame(data=None, index=GHI.index)
    diffuse_tracking['angle'] = 0.0
    diffuse_tracking['POA global'] = 0.0
    optimal_angle = 0
    
    for i in range(ghi.index.size):
        
        max_irradiance = 0

        for angle in range(-55,56,2):
            
            if angle < 0:
                surface_azimuth = 90 
                angle_abs = abs(angle)
            else:
                surface_azimuth = 270
                angle_abs = angle
            
            total_irrad = pvlib.irradiance.get_total_irradiance(surface_tilt=angle_abs, 
                                                                 surface_azimuth=surface_azimuth, 
                                                                 dni=dni.iloc[i], 
                                                                 ghi=ghi.iloc[i], 
                                                                 dhi=dhi.iloc[i], 
                                                                 solar_zenith=solar_position['apparent_zenith'].iloc[i], 
                                                                 solar_azimuth=solar_position['azimuth'].iloc[i],
                                                                 dni_extra=dni_extra.iloc[i],
                                                                 airmass=airmass.iloc[i],
                                                                 model='perez',
                                                                 model_perez='allsitescomposite1990')
            total_irradiance = total_irrad['poa_direct']
            
            #if solar_position['azimuth'].iloc[i] <= 180:
                #angle = -angle
            
            if total_irradiance > max_irradiance:
                max_irradiance = total_irradiance
                optimal_angle = angle
            
        diffuse_tracking['angle'].iloc[i] = optimal_angle
        diffuse_tracking['POA global'].iloc[i] = max_irradiance
    
    return diffuse_tracking

diffuse_tracking = find_optimal_rotation_angle(GHI, DHI, DNI, DNI_extra, airmass, solpos)

""" Comparison with true tracking """

truetracking_angles = pvlib.tracking.singleaxis(
    apparent_zenith=apparent_zenith,
    apparent_azimuth=azimuth,
    axis_tilt=axis_tilt,
    axis_azimuth=axis_azimuth,
    max_angle=max_angle,
    backtrack=False,  # for true-tracking
    gcr=GCR)  # irrelevant for true-tracking

true_tracking = pd.DataFrame(data=None, index=GHI.index)
true_tracking['tracker_theta'] = 0.0
true_tracking['POA_astronomical'] = 0.0
true_tracking['tracker_theta'] = truetracking_angles['tracker_theta'].fillna(0)

for i in range(true_tracking.index.size):
    
    angle = true_tracking["tracker_theta"].iloc[i]
        
    if angle < 0:
        surface_azimuth = 90 
        angle_abs = abs(angle)
    else:
        surface_azimuth = 270
        angle_abs = angle

    total_irrad = pvlib.irradiance.get_total_irradiance(surface_tilt=angle_abs, 
                                                        surface_azimuth=surface_azimuth, 
                                                        dni=real_weather["DNI"].iloc[i], 
                                                        ghi=real_weather["GHI"].iloc[i], 
                                                        dhi=real_weather["DHI"].iloc[i], 
                                                        solar_zenith=solpos['apparent_zenith'].iloc[i], 
                                                        solar_azimuth=solpos['azimuth'].iloc[i],
                                                        dni_extra=real_weather["DNI_extra"].iloc[i],
                                                        airmass=real_weather["airmass"].iloc[i],
                                                        model='perez',
                                                        model_perez='allsitescomposite1990')
    
    true_tracking["POA_astronomical"].iloc[i] = total_irrad["poa_global"]
    

""" Plot data """

# Irradiance GHI, DNI, DHI

"""real_weather["GHI"].plot(title='Irradiance generated from a clear sky model', label="GHI")
real_weather["DNI"].plot(title='Irradiance generated from a clear sky model', label="DNI")
real_weather["DHI"].plot(title='Irradiance generated from a clear sky model', label="DHI")"""

# Tracking curves & POA irradiance

fig, axes = plt.subplots(nrows=2, ncols=1, sharex=True)

diffuse_tracking['angle'].plot(title='Tracking Curve', label="Optimal tracking", ax=axes[0])
true_tracking["tracker_theta"].plot(title='Tracking Curve', label="Astronomical tracking",ax=axes[0])

diffuse_tracking['POA global'].plot(title='Irradiance', label="POA diffuse tracking", ax=axes[1])
true_tracking["POA_astronomical"].plot(title='Irradiance', label="POA astronomical tracking", ax=axes[1])

axes[0].legend(title="Tracker Tilt")
axes[1].legend(title="Irradiance")


plt.legend()
plt.show() 
    
    