import cv2
import os
import pytesseract
import re
import numpy as np
from datetime import datetime
from save_data import save_vehicle_log
import logging
from collections import Counter

# Setup logging for console messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tesseract OCR path (update if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

cascade_file = "model/haarcascade_russian_plate_number.xml"
valid_plate_regex = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{3,4}$'

min_area = 500
max_area = 15000
buffer_size = 5

logged_plates = set()
plate_text_buffer = []

def preprocess_plate(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    kernel_tophat = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    gray = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_tophat)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, sharpen_kernel)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 35, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        x, y, w, h = cv2.boundingRect(sorted(contours, key=cv2.contourArea, reverse=True)[0])
        if w > 50 and h > 15:
            thresh = thresh[y:y+h, x:x+w]
    return thresh

def clean_plate_text(text):
    text = re.sub(r'[^A-Z0-9]', '', text.upper())
    corrections = {'Q': 'O', '0': 'O', '1': 'I', '5': 'S', '8': 'B', '6': 'G',
                   '9': 'G', '4': 'A', '2': 'Z', ',': '', '-': ''}
    corrected = ''
    for i, ch in enumerate(text):
        if i < 2 and ch in corrections:
            corrected += corrections[ch]
        else:
            corrected += ch
    if re.match(valid_plate_regex, corrected):
        return corrected
    else:
        return ""

def save_plate_data(plate_text, img_roi, count):
    # 1. Save entry in CSV using save_data.py function
    save_vehicle_log(plate_text, slot="P12", gate="Entry", path="Straight → Left", status="IN")

    # 2. Save detected plate image in plates/plate_img folder
    save_path = f"plates/plate_img/detected_{plate_text}_{count}.jpg"
    cv2.imwrite(save_path, img_roi)

    # 3. Logging info
    logging.info(f"Saved vehicle entry: {plate_text} to CSV")
    logging.info(f"Saved plate image at: {save_path}")

def main():
    # Create directories if not exist
    os.makedirs("plates/plate_img", exist_ok=True)
    os.makedirs("model", exist_ok=True)

    plate_cascade = cv2.CascadeClassifier(cascade_file)
    if plate_cascade.empty():
        logging.error("Cascade file missing or failed to load!")
        return

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cap.set(cv2.CAP_PROP_FOCUS, 30)

    if not cap.isOpened():
        logging.error("Cannot open webcam")
        return

    count = 0
    logging.info("Starting detection, press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            logging.warning("Failed to read frame from webcam")
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        plates = plate_cascade.detectMultiScale(gray, 1.1, 3, minSize=(60, 20))

        if len(plates) == 0:
            cv2.imshow("Result", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        plates = sorted(plates, key=lambda b: b[2]*b[3], reverse=True)
        x, y, w, h = plates[0]
        area = w * h
        if not (min_area < area < max_area):
            cv2.imshow("Result", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        img_roi = frame[y:y+h, x:x+w]
        if img_roi.shape[0] < 20 or img_roi.shape[1] < 20:
            cv2.imshow("Result", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        processed_roi = preprocess_plate(img_roi)
        config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        raw_text = pytesseract.image_to_string(processed_roi, config=config).strip()
        cleaned_text = clean_plate_text(raw_text)

        if cleaned_text:
            plate_text_buffer.append(cleaned_text)
            if len(plate_text_buffer) > buffer_size:
                plate_text_buffer.pop(0)

            final_plate = Counter(plate_text_buffer).most_common(1)[0][0]

            if final_plate not in logged_plates:
                logging.info(f"Detected Plate: {final_plate}")

                # Save image and log to CSV
                save_plate_data(final_plate, img_roi, count)
                logged_plates.add(final_plate)
                count += 1

                # Show detected plate text on frame
                cv2.putText(frame, final_plate, (x, y-30), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 2)

        else:
            plate_text_buffer.clear()

        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
        cv2.putText(frame, "Number Plate", (x, y-5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255,0,255), 2)

        cv2.imshow("Result", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            logging.info("Exiting...")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
         