import numpy as np
import csv
import pandas as pd
import matplotlib.pyplot as plt


data = pd.read_csv('adc_data_20250623_130130.csv')
data.head() # to display the first 5 lines of loaded data
data[data.columns[[4,5,6]]].mean(0)
angles = [0,45,90,110]
FingerAngle = np.load('Finger_angle.npy')
GloveCal = np.load('Glove_cal.npy')

figure = plt.figure()
for i in range(3):
    plt.scatter(angles,FingerAngle[i])
    plt.plot(angles, (angles-+ GloveCal[i][1])/GloveCal[i][0] )
plt.xlabel("Angles (Degrees)")
plt.ylabel("Calculated Resistance (Ohm)")
plt.title("Calibration curves")
plt.show()
