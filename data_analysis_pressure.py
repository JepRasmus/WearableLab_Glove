import numpy as np
import csv
import pandas as pd


data = pd.read_csv('adc_data_20250623_130130.csv')
data.head() # to display the first 5 lines of loaded data
data[data.columns[[4,5,6]]].mean(0)