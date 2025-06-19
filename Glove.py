import numpy as np
import asyncio
from Multi_func import *
from Glove_calibration import collect_adc_data  # Adjust the import as needed


def calibrate_stretch(angles, time, finger):
    #angles: vec, time: milisec, finger: array
    y = np.zeros((len(angles),len(finger)))
    for i in finger:
        for j in angles:
            input("Put finger %i at %d degrees" % (finger[j], angles[i]))
            data = glove.get(time*fs)[:][finger]
            y[i][j] = np.mean(data)
    return y

duration = 5  # seconds

device = connectBLE()







adc_data = asyncio.run(collect_adc_data(duration))

for timestamp, values in adc_data:
    print(f"{timestamp} -> {values}")

input("press enter")

adc_data = asyncio.run(collect_adc_data(duration))

for timestamp, values in adc_data:
    print(f"{timestamp} -> {values}")

        
    




SamplePeriod = 200 # miliseconds
fs = glove.fs.get() # Get sampling freq
# cutoff = 10 # Lowpass cutoff as 10 Hz
# filtOrder = 2 # filter order 2
# signal = glove.signal.get(SamplePeriod) # Get signal with frq hz.

# signalFilt = np.zeros(np.size(signal))
# for i in range(np.size(signal,1)):
#     signalFilt[:][i] = butter_lowpass_filter(signal[:][i], cutoff, fs, filtOrder) # Filter the data.

    
# signalFilt = butter_lowpass_filter(signal, cutoff, fs, filtOrder) # Filter the data.


## Signal to angle
signalStretch = signalFilt[:][0:5]
signalPress = signalFilt[:][6:10]

signalStrechCal = calibrate.strech(signalStretch, strech)