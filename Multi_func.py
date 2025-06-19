import asyncio
import csv
import math
from datetime import datetime, timedelta
from bleak import BleakScanner, BleakClient

CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
# COLLECTION_DURATION_SECONDS = 5  # Set how long to collect per session
CSV_FILENAME = "adc_data.csv"

collected_data = []

def notification_handler(sender, data):
    try:
        values = [float(x) for x in data.decode().split(',')]
        timestamp = datetime.now()
        collected_data.append((timestamp, values))
        print(f"[{timestamp.strftime('%H:%M:%S')}] {values}")
    except ValueError as e:
        print(f"Invalid data: {data} — {e}")

async def scan_and_connect():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    device = next((d for d in devices if d.name and "jeppe is cool" in d.name.lower()), None)

    if not device:
        raise RuntimeError("BLE device with 'jeppe is Cool' not found.")

    client = BleakClient(device.address)
    await client.connect()
    print(f"Connected to {device.name}")
    return client

async def collect_once(client, duration_seconds):
    await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

    end_time = datetime.now() + timedelta(seconds=duration_seconds)
    while datetime.now() < end_time:
        await asyncio.sleep(0.1)

    await client.stop_notify(CHARACTERISTIC_UUID)
    print(f"Data collection ended after {duration_seconds} seconds.\n")

def save_to_csv(data, filename):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write header row
        writer.writerow(["timestamp", "value_1", "value_2", "value_3", "..."])
        for timestamp, values in data:
            writer.writerow([timestamp.isoformat()] + values)
    print(f"Data saved to {filename}")

async def main(COLLECTION_DURATION_SECONDS, finger, angle):
    client = await scan_and_connect()

    try:
        for i in range(finger*angle):
            user_input = input("Press Enter to collect data for Finger %i at degrees %d" %(math.floor(i/angle)+1, i%angle+1)).strip()
            if user_input.lower() == 'exit':
                break

            print("Collecting data...")
            await collect_once(client, COLLECTION_DURATION_SECONDS)
    finally:
        if client.is_connected:
            await client.disconnect()
            print("Disconnected from BLE device.")

    save_to_csv(collected_data, CSV_FILENAME)

# if __name__ == "__main__":
#     COLLECTION_DURATION_SECONDS = 5
#     asyncio.run(main(COLLECTION_DURATION_SECONDS, finger, angle))