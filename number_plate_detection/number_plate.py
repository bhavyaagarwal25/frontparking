import cv2
import os
import pytesseract
import re
import numpy as np
from datetime import datetime
from save_data import save_vehicle_entry
import urllib.request
import base64
import requests
import webbrowser

# Configure Tesseract path (for Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Create model directory if it doesn't exist
os.makedirs("model", exist_ok=True)

cascade_file = "model/haarcascade_license_plate.xml"

if not os.path.exists(cascade_file):
    cascade_url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_russian_plate_number.xml"
    urllib.request.urlretrieve(cascade_url, cascade_file)

plate_cascade = cv2.CascadeClassifier(cascade_file)
if plate_cascade.empty():
    print("Error: Cascade classifier not loaded properly!")
    exit(1)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam!")
    exit(1)

cap.set(3, 640)
cap.set(4, 480)

min_area = 500
max_area = 15000
count = 0
img_roi = None

os.makedirs("plates/plate_img", exist_ok=True)

logged_plates = set()

valid_plate_regex = r'^[A-Z]{2}\s?[0-9]{1,2}\s?[A-Z]{1,2}\s?[0-9]{4}$'

def preprocess_plate(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    return thresh

def clean_plate_text(text):
    text = text.upper().strip()
    text = re.sub(r'[^A-Z0-9\s]', '', text)
    text = re.sub(r'\s+', '', text)
    if len(text) >= 8:
        parts = [text[:2]]
        text = text[2:]
        numbers = re.findall(r'\d+', text)
        letters = re.findall(r'[A-Z]+', text)
        if numbers and letters:
            parts.extend([numbers[0][:2], letters[0], numbers[-1][:4]])
            return ''.join(parts)
    return text

print("Starting number plate detection... Press 'q' to quit.")

while True:
    success, img = cap.read()
    if not success:
        continue

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    plates = plate_cascade.detectMultiScale(img_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))

    for (x, y, w, h) in plates:
        area = w * h
        if min_area < area < max_area:
            img_roi = img[y:y+h, x:x+w]
            if img_roi.shape[0] < 20 or img_roi.shape[1] < 20:
                continue

            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img, "Number Plate", (x, y-5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 255), 2)

            processed_roi = preprocess_plate(img_roi)
            custom_configs = [
                r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            ]

            plate_text = ""
            for config in custom_configs:
                text = pytesseract.image_to_string(processed_roi, config=config).strip()
                if text and len(text) >= 8:
                    plate_text = text
                    break

            if plate_text:
                plate_text = clean_plate_text(plate_text)
                cv2.putText(img, plate_text, (x, y-30), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

                if re.match(valid_plate_regex, plate_text) and plate_text not in logged_plates:
                    print(f"Detected plate: {plate_text}")
                    save_vehicle_entry(plate_text, slot="P12", gate="Entry", path="Straight → Left", status="IN")
                    logged_plates.add(plate_text)

                    _, buffer = cv2.imencode('.jpg', img)
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')

                    response = requests.post("http://localhost:8080/upload", json={
                        "image": "data:image/png;base64," + jpg_as_text
                    })

                    if response.status_code == 200:
                        result = response.json()
                        plate_number = result.get("plate_number")
                        qr_path = result.get("qr_path")
                        if plate_number and qr_path:
                            print("\nPlate saved. Press ENTER to show QR code...")
                            input()
                            webbrowser.open(f"http://localhost:8080/{qr_path}")

                    cv2.imwrite(f"plates/plate_img/detected_{plate_text}_{count}.jpg", img_roi)
                    count += 1

    cv2.imshow("Result", img)
    if img_roi is not None:
        cv2.imshow("ROI", img_roi)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("Quitting application...")
        break

cap.release()
cv2.destroyAllWindows()
