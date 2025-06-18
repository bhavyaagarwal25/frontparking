

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import cv2
import numpy as np
import easyocr
import base64
import subprocess
import json
import csv
import os
from datetime import datetime
from save_data import save_vehicle_log

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='template')

print("Template folder path:", os.path.abspath('template'))
print("Files inside template:", os.listdir('template'))
app.secret_key = 'your_secret_key_here'  # Change this for production

plate_cascade = cv2.CascadeClassifier('haarcascade_russian_plate_number.xml')
reader = easyocr.Reader(['en'])

# Enable CORS for all routes (can be restricted if needed)
CORS(app)

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# -------- DEFAULT REDIRECT TO ADMIN LOGIN --------
@app.route('/')
def index():
    return redirect(url_for('admin_login'))

# -------- ADMIN LOGIN --------
@app.route('/adminlogin', methods=['GET', 'POST'])
def admin_login():
    if 'admin' in session:
        return redirect(url_for('admin_landing'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == 'admin' and password == 'adminpass':
            session['admin'] = username
            return redirect(url_for('admin_landing'))
        else:
            error = "Invalid admin credentials"
    return render_template('adminlogin.html', error=error)

# -------- ADMIN LANDING PAGE --------
@app.route('/admin/landing')
def admin_landing():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    return render_template('index.html')

#---------start Camera----
@app.route('/camera')
def camera_page():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    return render_template('camera.html')

# -------- ADMIN DASHBOARD --------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

#----------slot view------
@app.route('/slotview')
def slotview():
    return render_template('slotview.html')

#----------car records-------
@app.route('/carrecords')
def carrecords():
    return render_template('carrecords.html')

# -------- ADMIN LOGOUT --------
@app.route('/adminlogout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# -------- USER DASHBOARD (QR SCAN BASED) --------
@app.route('/userdashboard')
def user_dashboard():
    plate = request.args.get('plate', 'Unknown')
    slot = request.args.get('slot', 'N/A')
    time = request.args.get('time', 'N/A')

    # Optional: calculate a bill here based on slot/time (placeholder used below)
    bill = 50  # static or dynamic logic here
    raw_path = request.args.get('path', '')
    path = raw_path.split(',') if raw_path else [f'Main Gate', f'Slot {slot}']

    return render_template('user_dashboard.html', plate=plate, entry_time=time, path=path, bill=bill)

# Helper function to save cropped plate image
def save_plate_image(image, plate_text):
    folder_path = 'plates/plate_img'
    os.makedirs(folder_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{plate_text}_{timestamp}.jpg"
    filepath = os.path.join(folder_path, filename)
    cv2.imwrite(filepath, image)
    return filepath

# Helper function to log data into CSV
def log_vehicle(plate_text, slot):
    log_file = 'vehicle_logs.csv'
    file_exists = os.path.isfile(log_file)
    with open(log_file, 'a', newline='') as csvfile:
        fieldnames = ['Plate', 'slot', 'Timestamp']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'Plate': plate_text.strip().replace(" ", ""),
            'slot': slot if slot else 'N/A',
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

# -------- OCR IMAGE UPLOAD --------@app.route('/upload', methods=['POST'])
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        img_data = request.json.get('image', '')
        if not img_data or ',' not in img_data:
            return jsonify({'error': 'Invalid image data'}), 400

        img_str = img_data.split(',')[1]
        img_bytes = base64.b64decode(img_str)
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'Failed to decode image'}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        print("Plates detected:", plates)

        plate_text = "Not Detected"
        cropped_plate_img = None

        for (x, y, w, h) in plates:
            cropped_plate_img = img[y:y+h, x:x+w]
            plate_gray = cv2.cvtColor(cropped_plate_img, cv2.COLOR_BGR2GRAY)
            plate_resized = cv2.resize(plate_gray, (1024, 256))
            plate_text = read_plate_text(plate_resized)
            print("OCR Plate Text:", plate_text)
            break

        if plate_text == "Not Detected" or cropped_plate_img is None:
            return jsonify({"error": "Plate number not detected. Please retake the photo."}), 400

        plate_text = plate_text.strip().replace(" ", "")
        save_plate_image(cropped_plate_img, plate_text)

        try:
            result = subprocess.run(['./parking', plate_text], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return jsonify({'plate_number': plate_text, 'error': 'Parking allocation failed'}), 500

            output_json = result.stdout.strip()
            try:
                output = json.loads(output_json)
            except Exception:
                output = {}
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if "slot" in line.lower():
                        output['slot'] = line.split(':')[-1].strip()
                    if "path" in line.lower():
                        output['path'] = line.split(':')[-1].strip().split()

            slot = output.get('slot', 'N/A')
            path = output.get('path', [])
            entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            log_vehicle(plate_text, slot)

            # ✅ Return JSON instead of redirect
            return jsonify({
                'plate_number': plate_text,
                'slot': slot,
                'time': entry_time,
                'path': path
            })

        except Exception as e:
            return jsonify({
                "plate_number": plate_text,
                "error": f"Allocation backend failed: {str(e)}"
            }), 500

    except Exception as e:
        print("Error during upload:", str(e))
        return jsonify({"error": "Failed to process image"}), 500


# -------- OCR FUNCTION --------
def read_plate_text(image):
    results = sorted(reader.readtext(image), key=lambda x: x[2], reverse=True)
    for (bbox, text, prob) in results:
        if len(text) > 3:
            return text.strip()
    return "Not Detected"

# -------- SLOT ALLOCATION VIA API --------
import subprocess
import json  # ✅ Required to parse JSON from C++ output

@app.route('/allocate', methods=['POST'])
def allocate_slot():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    plate_number = data.get('plateNumber')

    if not plate_number:
        return jsonify({'error': 'No plate number provided'}), 400

    try:
        result = subprocess.run(['./parking', plate_number], capture_output=True, text=True, timeout=10)
        print("Subprocess output:\n", result.stdout)

        if result.returncode != 0:
            return jsonify({
                "plate_number": plate_number,
                "error": "No available slot or error occurred",
                "raw_output": result.stdout
            }), 400

        # ✅ Parse JSON output from C++ safely
        try:
            cxx_output = json.loads(result.stdout)
        except json.JSONDecodeError:
            return jsonify({'error': 'C++ output not in JSON format', 'raw_output': result.stdout}), 500

        slot = cxx_output.get("slot")
        path = cxx_output.get("path")
        if not slot:
            return jsonify({'error': 'Slot not found in C++ output', 'raw_output': result.stdout}), 500
        print(slot)
        return jsonify({
            "plate_number": cxx_output.get("plate"),
            "slot": slot,
            "path": path
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error running allocation: {str(e)}'}), 500

# -------- MAIN --------
print("Ready to run Flask app...")
if __name__ == '__main__':
    # It's better to listen on 0.0.0.0 to be accessible from network, change debug=False for production
    app.run(debug=True, host='0.0.0.0', port=8080)