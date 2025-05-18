import csv
import os
from datetime import datetime

def save_vehicle_log(plate_number):
    # Plate number ke aage ya peeche agar extra space ho toh hatao
    plate_number = plate_number.strip().replace(" ", "")
    
    log_path = 'vehicle_logs.csv'
    entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    file_exists = os.path.isfile(log_path)

    with open(log_path, 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Plate', 'Timestamp'])  # header row
        writer.writerow([plate_number, entry_time])
