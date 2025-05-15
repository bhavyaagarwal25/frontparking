from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import cv2
import numpy as np
import easyocr
import base64
from datetime import datetime

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
#-------qr code-------
@app.route('/qrcode/<plate>')
def qrcode_page(plate):
    # QR code image URL generate karo (ya backend me generate karke yahan bhejo)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=http://localhost:8080/userdashboard/{plate}"
    return render_template('qrcode.html', plate=plate, qr_url=qr_url)
# -------- USER DASHBOARD (QR SCAN BASED) --------
@app.route('/userdashboard/<plate>')
def user_dashboard_qr(plate):
    entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bill = 30  # Example static bill
    path = "Entry Gate → Slot A3"  # Example path
    return render_template("user_dashboard.html", username=plate, entry_time=entry_time, path=path, bill=bill)

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
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        resized_img = cv2.resize(thresh, (1024, 1024))
        plate_number = read_plate_text(resized_img)

        return jsonify({"plate_number": plate_number})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to process image"}), 500

# -------- OCR FUNCTION --------
def read_plate_text(image):
    results = reader.readtext(image)
    for (bbox, text, prob) in results:
        if len(text) > 3:
            return text
    return "Not Detected"

# -------- MAIN --------
if __name__ == '__main__':
    app.run(debug=True, port=8080)
