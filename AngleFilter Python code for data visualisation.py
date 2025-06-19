import asyncio
import threading
import queue
import time
import csv
from  Glove_calibration import *
import numpy as np
from datetime import datetime

import matplotlib.pyplot as plt
from bleak import BleakScanner, BleakClient

CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# Thread-safe queue to store data for plotting and CSV-writing
data_queue = queue.Queue()

# Event to signal when to stop BLE notifications
stop_event = threading.Event() 

# Name for CSV file
csv_filename = f'adc_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

# def RunningMedian(x,N):
#     idx = np.arange(N) + np.arange(len(x)-N+1)[:,None]
#     b = [row[row>0] for row in x[idx]]
#     return np.array(map(np.median,b))

def notification_handler(sender, data):
    """
    This callback executes in Bleak's event loop (the separate thread).
    It parses data and places it into the queue. The main thread will
    handle CSV-writing and plotting.
    """
    # Assume the data is a comma-separated string, e.g. "-1.00, 2.50, 3.00, ..."
    decoded_data = data.decode().split(',')
    timestamp = datetime.now()

    try:
        # Parse each value as a float
        values = [float(x) for x in decoded_data]
    except ValueError as e:
        # If there's any invalid float, skip and log the error
        print(f"Skipping invalid data: {decoded_data}, error: {e}")
        return

    # Put data (timestamp + values) into the queue for the main thread
    data_queue.put((timestamp, values))


async def bleak_main():
    """
    - Discover and connect to the BLE device
    - Start notifications
    - Remain active until stop_event is signaled
    """
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    device = next((d for d in devices if d.name and "jeppe is 2 cool" in d.name.lower()), None)
    #jeppe is cool

    if not device:
        print("Device not found. Exiting BLE thread.")
        return

    print(f"Found device: {device.name} ({device.address}). Attempting to connect...")
    async with BleakClient(device.address) as client:
        print(f"Connected to {device.name}!")

        # Start BLE notifications
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        print("Notifications started. Waiting for stop_event...")

        # Keep the async loop alive until we set stop_event
        while not stop_event.is_set():
            await asyncio.sleep(0.1)

        # Optionally stop notifications if desired
        await client.stop_notify(CHARACTERISTIC_UUID)
        print("Stopped notifications.")

    print("BLE thread exiting.")


def run_bleak_loop():
    """Target for the separate thread to run BLE asynchronously."""
    asyncio.run(bleak_main())


if __name__ == "__main__":
    ### Cockpit ####
    # A buffer to hold the most recent data for plotting
    data_buffer = []
    data_filtered = []
    finger_cal = []
    buffer_size = 2000  # keep up to 100 data points
    filterWindow = 10
    calibrate_wait = 5 #seconds to measure each finger
    fingers = [1,2,3] # using channel 6,7,8,.. respectively
    angles = [0,45,90,110] # angles to put fingers in
    file_name = "Glove_cal.npy"
    show_raw_plt = False
    
    # Try to find finger/angle calibrations. If none ask to make them
    try:
        finger_cal = np.load('glove_cal.npy') # Finger_cal[finger][coef,intercept]
    except FileNotFoundError:
        print('Seems like you havn\'t calibrated \n Would you like to do so now?')
        usrInput = input('[Y]es/[n]o \n')
        if usrInput.lower() in ['y', 'yes']:
            asyncio.run(glove_calibrate(calibrate_wait, fingers, angles,file_name))
            finger_cal = np.load(file_name)
    # Start the BLE thread
    ble_thread = threading.Thread(target=run_bleak_loop, daemon=True)
    ble_thread.start()

    # --------------------
    # Set up real-time plot
    # --------------------
    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 6))
    fig2, ax2 = plt.subplots(figsize=(12,6))

    # We’ll initialize lines once we know the number of channels
    lines = []
    lines2 = []
    num_channels = 0

    # Track whether we have written the CSV header yet
    csv_header_written = False

    # For measuring relative time on the X-axis
    first_timestamp = None

    try:
        while True:
            # Retrieve any new data from the queue
            while not data_queue.empty():
                timestamp, values = data_queue.get()

                # If this is the first data, set up channels
                if num_channels == 0:
                    num_channels = len(values)
                    num_channels = 10

                # If we haven't set up the plot lines yet, do it now
                if not lines or not lines2:
                    for i in range(num_channels):
                        line, = ax.plot([], [], label=f'Channel {i+1}')
                        line2, = ax2.plot([], [], label=f'Channel {i+1}')

                        lines.append(line)
                        lines2.append(line2)

                    ax.set_xlabel('Time (s)')
                    ax2.set_xlabel('Time (s)')

                    ax.set_ylabel('ADC Value')
                    ax2.set_ylabel('Angle (degrees)')

                    ax.set_title('Real-time ADC Data')
                    ax2.set_title('Real-time Angle Data')

                    ax.legend(loc = 'upper left')
                    ax2.legend(loc = 'upper left')


                # If we haven't written the CSV header, do it now
                if not csv_header_written:
                    with open(csv_filename, 'w', newline='') as file:
                        writer = csv.writer(file)
                        header = ['Timestamp'] + [f'Channel_{i+1}' for i in range(num_channels)]
                        writer.writerow(header)
                    csv_header_written = True

                # Append data to buffer
                if first_timestamp is None:
                    first_timestamp = timestamp
                
                filter_value = np.mean([x[1] for x in data_buffer[-filterWindow:]] + [values],0).tolist()

                data_buffer.append((timestamp, values))
                # data_filtered.append((timestamp, filter_value))
                data_filtered = data_filtered + [filter_value]

                if len(data_buffer) > buffer_size:
                    data_buffer.pop(0)
                    data_filtered.pop(0)

                # Write this data row to CSV (append mode)
                with open(csv_filename, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([timestamp] + values)

            # Update the plot if we have data
            if data_filtered and (lines or lines2):
                # Generate array of times in seconds relative to the first timestamp
                times = [(dp[0] - first_timestamp).total_seconds() for dp in data_buffer]

                # Update each channel’s line data
                if show_raw_plt:
                    for i in range(num_channels):
                        channel_vals = [row[i] for row in data_filtered]
                        lines[i].set_data(times, channel_vals)

                if finger_cal.any():
                    for i in range(len(fingers)):
                        finger_vals = [row[5+i] for row in data_filtered]
                        angle_vals = np.array(finger_vals)*finger_cal[i][0] + finger_cal[i][1]
                        lines2[i].set_data(times, angle_vals)

                ax.relim()
                ax2.relim()
                ax.autoscale_view()
                ax2.autoscale_view()

            # Redraw the figure
            fig.canvas.draw()
            fig2.canvas.draw()
            fig.canvas.flush_events()
            fig2.canvas.flush_events()


            # If the figure is closed, break
            if not plt.fignum_exists(fig.number):
                break

            # Short pause to avoid maxing out CPU
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")

    finally:
        # Signal the BLE thread to stop
        stop_event.set()
        ble_thread.join()

        # Clean up the plot
        plt.close(fig)
        print("Done.")
