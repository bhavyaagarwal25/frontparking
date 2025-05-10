# save_data.py
import csv
from datetime import datetime

def save_vehicle_entry(plate_text, slot="N/A", gate="Entry", path="N/A", status="IN"):
    with open('vehicle_logs.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, plate_text.strip(), slot, gate, path, status])
