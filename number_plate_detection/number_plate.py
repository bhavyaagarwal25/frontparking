import cv2
import os
import easyocr
import re
from datetime import datetime
from save_data import save_vehicle_entry

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Load the Haar Cascade classifier for number plates
harcascade = "model/haarcascade_russian_plate_number.xml"
plate_cascade = cv2.CascadeClassifier(harcascade)

# Video capture from webcam
cap = cv2.VideoCapture(0)

# Set the frame width and height
cap.set(3, 640)  # Width
cap.set(4, 480)  # Height

# Minimum area for detecting the plate
min_area = 500
count = 0
img_roi = None

# Directory to save the plates
os.makedirs("plates/plate_img", exist_ok=True)

# Set to track logged plates
logged_plates = set()

# Invalid keywords for filtering
invalid_keywords = ['Numper Plate', 'nunber Plate', 'Number Plate', 'Wl', 'Tumber Plate']

# Regular expression for valid number plate formats (example)
valid_plate_regex = r'^[A-Z]{2}\s?[0-9A-Z]{1,2}\s?[0-9]{4,6}$'

while True:
    success, img = cap.read()

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect plates in the image using Haar Cascade
    plates = plate_cascade.detectMultiScale(img_gray, 1.1, 4)

    for (x, y, w, h) in plates:
        area = w * h

        if area > min_area:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0))
            cv2.putText(img, "Number Plate", (x, y - 5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 255), 2)
            img_roi = img[y: y + h, x: x + w]
            cv2.imshow("ROI", img_roi)

            # OCR to extract text from the ROI (Region of Interest)
            result = reader.readtext(img_roi)
            plate_text = ""

            for detection in result:
                plate_text += detection[1] + " "

            # Display the detected plate text on the image
            cv2.putText(img, plate_text.strip(), (x, y - 30), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

            # Filter invalid text (such as common OCR errors)
            plate_text = plate_text.strip()
            if any(keyword in plate_text for keyword in invalid_keywords):
                plate_text = ""  # Skip invalid plates

            # Check if the plate follows the valid format using regex
            if re.match(valid_plate_regex, plate_text):
                plate_text = plate_text.replace(" ", "").replace(";", "").replace("]", "").replace(",", "")

                # Avoid duplicates by checking the logged plates set
                if plate_text and plate_text not in logged_plates:
                    save_vehicle_entry(plate_text, slot="P12", gate="Entry", path="Straight → Left", status="IN")
                    logged_plates.add(plate_text)

    # Display the processed frame
    cv2.imshow("Result", img)

    # Keyboard interaction: Save the scanned plate image or quit the application
    key = cv2.waitKey(1) & 0xFF

    # Save the scanned plate image if 's' is pressed
    if key == ord('s') and img_roi is not None:
        cv2.imwrite(f"plates/plate_img/scanned_img_{count}.jpg", img_roi)
        cv2.rectangle(img, (0, 200), (640, 300), (0, 255, 0), cv2.FILLED)
        cv2.putText(img, "Plate Saved", (150, 265), cv2.FONT_HERSHEY_COMPLEX_SMALL, 2, (0, 0, 255), 2)
        cv2.imshow("Results", img)
        cv2.waitKey(500)
        count += 1
    # Exit the loop if 'q' is pressed
    elif key == ord('q'):
        break

# Release the webcam and close OpenCV windows
cap.release()
cv2.destroyAllWindows()
