# import asyncio
# import numpy as np
# from datetime import datetime, timedelta
# from bleak import BleakScanner, BleakClient
# from sklearn.linear_model import LinearRegression

# CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# async def glove_calibrate(duration_seconds: float, fingers: list, angles: list, file_name: str):
#     """
#     Connects to the BLE device and collects ADC data for the specified duration.
    
#     Returns:
#         A list of (timestamp, [float, float, ...]) tuples.
#     """
#     collected_data = []
#     fingerAngle = np.zeros((len(fingers),len(angles)))
#     finger_cal = np.zeros((len(fingers),2))


#     def notification_handler(sender, data):
#         try:
#             values = [float(x) for x in data.decode().split(',')]
#             timestamp = datetime.now()
#             collected_data.append((timestamp, values))
#         except ValueError as e:
#             print(f"Skipping invalid data: {data}, error: {e}")

#     print("Scanning for BLE devices...")
#     devices = await BleakScanner.discover()
#     device = next((d for d in devices if d.name and "jeppe is 2 cool" in d.name.lower()), None)

#     if not device:
#         raise RuntimeError("BLE device with 'Jeppe is Cool' not found.")

#     async with BleakClient(device.address) as client:
#         print(f"Connected to {device.name}. Starting data collection...")
#         for i in range(len(fingers)):
#             for j in range(len(angles)):
#                 input("Press Enter to collect data for Finger %i at degrees %d" %(fingers[i], angles[j]))
#                 await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

#                 end_time = datetime.now() + timedelta(seconds=duration_seconds)
#                 while datetime.now() < end_time:
#                     await asyncio.sleep(0.1)

#                 await client.stop_notify(CHARACTERISTIC_UUID)
#                 print("Stopped notifications.")
#                 fingerAngle[i,j] = np.mean([x[1] for x in collected_data],0)[i]
#                 collected_data = []
            
#             model = LinearRegression().fit(fingerAngle[i,:].reshape(-1,1), angles)
#             finger_cal[i][0] = model.coef_.item()
#             finger_cal[i][1] = model.intercept_
#         np.save(file_name, finger_cal)
#     return finger_cal

# if __name__ == "__main__":
#     finger_cal = asyncio.run(glove_calibrate(5, [1, 2, 3], [0, 45, 90, 110]),"glove_cal")
    

import asyncio
import numpy as np
from datetime import datetime, timedelta
from bleak import BleakScanner, BleakClient
from sklearn.linear_model import LinearRegression

CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

async def glove_calibrate(duration_seconds: float, fingers: list, angles: list, file_name: str):
    fingerAngle = np.zeros((len(fingers), len(angles)))
    finger_cal = np.zeros((len(fingers), 2))

    collecting = False  # Flag to control data collection
    collected_data = []  # Buffer for the current calibration
    current_finger = None

    def notification_handler(sender, data):
        nonlocal collecting
        if not collecting:
            return  # Ignore data when not collecting
        try:
            values = [float(x) for x in data.decode().split(',')]
            timestamp = datetime.now()
            collected_data.append((timestamp, values))
        except ValueError as e:
            print(f"Skipping invalid data: {data}, error: {e}")

    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    device = next((d for d in devices if d.name and "jeppe is 2 cool" in d.name.lower()), None)
    if not device:
        raise RuntimeError("BLE device not found.")

    async with BleakClient(device.address) as client:
        print(f"Connected to {device.name}. Waiting for calibration instructions...")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        for i in range(len(fingers)):
            for j in range(len(angles)):
                input(f"Press Enter to collect data for Finger {fingers[i]} at {angles[j]} degrees...")
                collecting = True
                collected_data.clear()  # reset buffer

                # Run for specified duration
                end_time = datetime.now() + timedelta(seconds=duration_seconds)
                while datetime.now() < end_time:
                    await asyncio.sleep(0.05)

                collecting = False

                # Compute mean of the i-th finger's channel
                fingerAngle[i, j] = np.mean([x[1][i] for x in collected_data])  # average this finger's column
                print(f"Mean ADC value for finger {fingers[i]} at {angles[j]} deg: {fingerAngle[i, j]}")

            # Fit a simple linear regression per finger
            model = LinearRegression().fit(
                fingerAngle[i, :].reshape(-1, 1), angles
            )
            finger_cal[i, 0] = model.coef_.item()
            finger_cal[i, 1] = model.intercept_

        # Save calibration
        np.save(file_name, finger_cal)
        np.save('Finger_angle', fingerAngle)
        print("Calibration saved!")

    return finger_cal

# Usage:
if __name__ == "__main__":
    finger_cal = asyncio.run(
        glove_calibrate(5, [1, 2, 3], [0, 45, 90, 110], "glove_cal.npy")
    )
