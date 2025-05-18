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
from collections import Counter
import logging

# Setup logging instead of print
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Ensure model directory exists
os.makedirs("model", exist_ok=True)

cascade_file = "model/haarcascade_russian_plate_number.xml"
if not os.path.exists(cascade_file):
    logging.info("Downloading Haar cascade for plate detection...")
    cascade_url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_russian_plate_number.xml"
    urllib.request.urlretrieve(cascade_url, cascade_file)
    logging.info("Download complete.")

plate_cascade = cv2.CascadeClassifier(cascade_file)
if plate_cascade.empty():
    logging.error("Failed to load Haar cascade classifier! Exiting.")
    exit(1)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    logging.error("Could not open webcam! Exiting.")
    exit(1)

# Disable autofocus and set manual focus (if supported)
cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
cap.set(cv2.CAP_PROP_FOCUS, 30)

min_area = 500
max_area = 15000
count = 0

os.makedirs("plates/plate_img", exist_ok=True)

logged_plates = set()

# Regex for Indian number plate format: e.g. KA01AB1234
valid_plate_regex = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{3,4}$'

plate_text_buffer = []
buffer_size = 5  # Number of frames to buffer OCR results

def preprocess_plate(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    kernel_tophat = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    gray = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_tophat)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, sharpen_kernel)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 35, 10
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # Crop to largest contour (likely text)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        x, y, w, h = cv2.boundingRect(contours[0])
        if w > 50 and h > 15:
            thresh = thresh[y:y+h, x:x+w]
    return thresh

def clean_plate_text(text):
    text = text.upper().strip()
    text = re.sub(r'[^A-Z0-9]', '', text)

    corrections = {
        'Q': 'O',
        '0': 'O',
        '1': 'I',
        '5': 'S',
        '8': 'B',
        '6': 'G',
        '9': 'G',
        '4': 'A',
        '2': 'Z',
        ',': '',
        '-': '',
    }

    corrected = ''
    for i, ch in enumerate(text):
        if i < 2:  # first two chars should be letters (state code)
            corrected += corrections.get(ch, ch) if ch.isdigit() else ch
        else:
            corrected += corrections.get(ch, ch)

    if re.match(valid_plate_regex, corrected):
        return corrected
    return ""

logging.info("Starting number plate detection... Press 'q' to quit.")

while True:
    success, img = cap.read()
    if not success:
        logging.warning("Failed to grab frame from webcam.")
        continue

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    plates = plate_cascade.detectMultiScale(img_gray, scaleFactor=1.1, minNeighbors=3, minSize=(60,20), flags=cv2.CASCADE_SCALE_IMAGE)

    if len(plates) == 0:
        cv2.imshow("Result", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            logging.info("Quitting application...")
            break
        continue

    plates = sorted(plates, key=lambda b: b[2]*b[3], reverse=True)
    x, y, w, h = plates[0]
    area = w * h

    if area < min_area or area > max_area:
        cv2.imshow("Result", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            logging.info("Quitting application...")
            break
        continue

    img_roi = img[y:y+h, x:x+w]
    if img_roi.shape[0] < 20 or img_roi.shape[1] < 20:
        cv2.imshow("Result", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            logging.info("Quitting application...")
            break
        continue

    cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
    cv2.putText(img, "Number Plate", (x, y-5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 255), 2)

    processed_roi = preprocess_plate(img_roi)

    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    raw_text = pytesseract.image_to_string(processed_roi, config=custom_config).strip()
    logging.debug(f"OCR raw text: '{raw_text}'")
    cleaned_text = clean_plate_text(raw_text)
    logging.info(f"Cleaned plate text: '{cleaned_text}'")

    if cleaned_text:
        plate_text_buffer.append(cleaned_text)
        if len(plate_text_buffer) > buffer_size:
            plate_text_buffer.pop(0)

        final_plate = Counter(plate_text_buffer).most_common(1)[0][0]

        if final_plate and final_plate not in logged_plates:
            logging.info(f"Detected plate: {final_plate}")
            cv2.putText(img, final_plate, (x, y-30), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

            try:
                save_vehicle_entry(final_plate, slot="P12", gate="Entry", path="Straight → Left", status="IN")
            except Exception as e:
                logging.error(f"Error saving vehicle entry: {e}")

            logged_plates.add(final_plate)

            _, buffer = cv2.imencode('.jpg', img)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            try:
                response = requests.post("http://localhost:8080/upload", json={
                    "image": "data:image/png;base64," + jpg_as_text
                })
                if response.status_code == 200:
                    result = response.json()
                    plate_number = result.get("plate_number")
                    qr_path = result.get("qr_path")
                    if plate_number and qr_path:
                        logging.info("Plate saved successfully. Press ENTER to show QR code...")
                        input()
                        webbrowser.open(f"http://localhost:8080/{qr_path}")
                else:
                    logging.warning(f"Server responded with status code: {response.status_code}")
            except Exception as e:
                logging.error(f"Error uploading image: {e}")

            cv2.imwrite(f"plates/plate_img/detected_{final_plate}_{count}.jpg", img_roi)
            count += 1
    else:
        plate_text_buffer.clear()

    cv2.imshow("Result", img)
    if 'img_roi' in locals() and img_roi is not None:
        cv2.imshow("ROI", img_roi)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        logging.info("Quitting application...")
        break

cap.release()
cv2.destroyAllWindows()
