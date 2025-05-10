from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import easyocr
import base64
from datetime import datetime

app = Flask(__name__)

# Load Haar cascade for number plate detection
plate_cascade = cv2.CascadeClassifier('haarcascade_russian_plate_number.xml')

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Function to process the image and detect the plate number
def read_plate_text(image):
    results = reader.readtext(image)
    print(f"OCR Results: {results}")  # Debug: Print all OCR results

    # Loop through the OCR results
    for (bbox, text, prob) in results:
        if len(text) > 3:  # Only consider results with significant length
            return text
    return "Not Detected"

# Enable CORS
CORS(app, resources={r"/upload": {"origins": "*"}})

@app.route('/upload', methods=['POST'])  # Ensure POST method is allowed here
def upload_image():
    try:
        # Get the image from the POST request
        data = request.get_json()
        img_data = data.get('image')

        # Decode the base64 image
        img_str = img_data.split(',')[1]  # Remove the 'data:image/png;base64,' part
        img_bytes = base64.b64decode(img_str)
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Preprocessing the image for OCR
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Optionally apply some thresholding to improve contrast (adaptive thresholding is a good choice)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)

        # Resize the image (if it's too small)
        resized_img = cv2.resize(thresh, (1024, 1024))

        # Detect the plate number using EasyOCR
        plate_number = read_plate_text(resized_img)

        # Return the plate number as a JSON response
        return jsonify({"plate_number": plate_number})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to process image"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
