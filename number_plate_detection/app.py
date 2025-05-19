from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import cv2
import numpy as np
import easyocr
import base64
import subprocess
import csv
from datetime import datetime
from save_data import save_vehicle_log
app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='template')
import os
print("Template folder path:", os.path.abspath('template'))
print("Files inside template:", os.listdir('template'))
app.secret_key = 'your_secret_key_here'  # Change this for production

plate_cascade = cv2.CascadeClassifier('haarcascade_russian_plate_number.xml')
reader = easyocr.Reader(['en'])

CORS(app, resources={r"/upload": {"origins": "*"}})
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
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
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
#----------car recordes-------
@app.route('/carrecords')
def carrecords():
    return render_template('carrecords.html')
# -------- ADMIN LOGOUT --------
@app.route('/adminlogout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))
# #-------qr code-------
# @app.route('/qrcode/<plate>')
# def qrcode_page(plate):
#     # QR code image URL generate karo (ya backend me generate karke yahan bhejo)
#     # qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=http://localhost:8080/userdashboard/{plate}"

#     qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=http://localhost:8080/userdashboard"

#     return render_template('qrcode.html', plate=plate, qr_url=qr_url)

# -------- USER DASHBOARD (QR SCAN BASED) --------
@app.route('/userdashboard')
def user_dashboard():
    try:
        with open('vehicle_logs.csv', 'r') as csvfile:
            rows = list(csv.DictReader(csvfile))
            if not rows:
                return "No vehicle records found."
            latest = rows[-1]  # Get the most recent record
            plate = latest['Plate']
            entry_time = latest['Timestamp']
    except Exception as e:
        return f"Error reading log: {e}"
    path= []
    try:
        result = subprocess.run(['./parking', plate], capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0 or "ERROR" in result.stdout:
                path =["No path available "]
        else:   
            output = result.stdout.strip().split('\n')
        
            for line in output:
                if line.startswith("Path from entry"):
                    path_str = line.split(':')[1].strip()
                    path = path_str.split()
    except Exception as e:
        path =["Error fetching path"]

    bill = 80  # You can make this dynamic later

    # entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # bill = 30  # Example static bill
    # path = "Entry Gate → Slot A3"  # Example path

    return render_template("user_dashboard.html", plate=plate, entry_time=entry_time, path=path, bill=bill)


# Helper function to save cropped plate image
def save_plate_image(image, plate_text):
    # Folder path jahan images save karni hain
    folder_path = 'plates/plate_img'
    os.makedirs(folder_path, exist_ok=True)

    # Filename: plate number + timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{plate_text}_{timestamp}.jpg"
    filepath = os.path.join(folder_path, filename)

    # Image save karna
    cv2.imwrite(filepath, image)
    return filepath


# Helper function to log data into CSV
def log_vehicle(plate_text,slot):
    log_file = 'vehicle_logs.csv'
    file_exists = os.path.isfile(log_file)
    with open(log_file, 'a', newline='') as csvfile:
        fieldnames = ['Plate','slot', 'Timestamp']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'Plate': plate_text.strip().replace(" ", ""),
             'slot': slot if slot else 'N/A',
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
# -------- OCR IMAGE UPLOAD --------
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()
        img_data = data.get('image')
        img_str = img_data.split(',')[1]
        img_bytes = base64.b64decode(img_str)
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        plate_text = "Not Detected"
        cropped_plate_img = None

        for (x, y, w, h) in plates:
            cropped_plate_img = img[y:y+h, x:x+w]  # Crop plate area from original colored image
            plate_gray = cv2.cvtColor(cropped_plate_img, cv2.COLOR_BGR2GRAY)
            plate_resized = cv2.resize(plate_gray, (1024, 256))  # Resize width-wise for better OCR
            plate_text = read_plate_text(plate_resized)
            break  # only first detected plate

        if plate_text != "Not Detected" and cropped_plate_img is not None:
            save_plate_image(cropped_plate_img, plate_text)
            #log_vehicle(plate_text)
            try:
                result = subprocess.run(['./parking', plate_text], capture_output=True, text=True, timeout=5)
                output = result.stdout.strip().split('\n')
                slot = None
                path = []
                for line in output:
                    if line.startswith("Best Slot:"):
                        slot = line.split(':')[1].strip()
                    elif line.startswith("Path from entry"):
                        path_str = line.split(':')[1].strip()
                        path = path_str.split()
                log_vehicle(plate_text, slot)
                return jsonify({
                    "plate_number": plate_text,
                    "slot": slot if slot else 'N/A',
                    
                })
            except Exception as e:
                return jsonify({
                    "plate_number": plate_text,
                    "error": f"Allocation backend failed: {str(e)}"
                }), 500

        return jsonify({"plate_number": plate_text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to process image"}), 500


# -------- OCR FUNCTION --------
def read_plate_text(image):
    #results = reader.readtext(image)
    results = sorted(reader.readtext(image), key=lambda x: x[2], reverse=True)
    plate_text = results[0][1] if results else "Not Detected"

    for (bbox, text, prob) in results:
        if len(text) > 3:
            return text
    return "Not Detected"



@app.route('/allocate', methods=['POST'])
def allocate_slot():
    data = request.get_json()
    plate_number = data.get('plateNumber')
    timestamp = data.get("timestamp")
    if not plate_number:
        return jsonify({'error': 'No plate number provided'}), 400
    
    # Call your compiled C++ program with plate number as argument
    # Assume your C++ program binary is './parking' and it accepts plate number
    try:
        result = subprocess.run(['./parking', plate_number], capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0 or "ERROR" in result.stdout:
            return jsonify({
                "plate_number": plate_number,
                "error": "No available slot found"
             }), 400
        output = result.stdout.strip().split('\n')
        
        slot = None
        for line in output:
            if line.startswith("Best Slot:"):
                slot = line.split(':')[1].strip()

        return jsonify({'slot': slot})

    except Exception as e:
        return jsonify({'error': f'Error running allocation: {str(e)}'}), 500

# -------- MAIN --------
if __name__ == '__main__':
    app.run(debug=True, port=8080)
