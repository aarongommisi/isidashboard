import os
import subprocess
from flask import Flask, request, redirect, url_for, flash, send_from_directory, Response, render_template, render_template_string, jsonify
from werkzeug.utils import secure_filename
import io
import zipfile
import sqlite3


UPLOAD_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'Is1S3cr3tk3y'

# Database Configuration
DATABASE = './static/exam_results.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            score INTEGER,
            total_questions INTEGER,
            percentage REAL
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/', methods=['GET'])
def root():
    return render_template('index.html')

@app.route('/quiz', methods=['GET'])
def quiz():
    return render_template('mockexam.html')

@app.route('/upload')
def page1():
    return render_template('upload.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_files():
    if request.method == 'POST':
        files = request.files.getlist('files[]')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                flash(f"{filename} uploaded successfully.")
            else:
                flash("Invalid file type.")
    return "Files uploaded."

@app.route('/process', methods=['POST'])
def process_files():
    business_entity = request.args.get('business_entity', '')
    script_path = "./static/pdfextract.py"  # Path to your pdfextract.py script

    command = [
        "python",
        script_path,
        "--input",
        UPLOAD_FOLDER,
        "--output",
        OUTPUT_FOLDER,
        "--processed",
        PROCESSED_FOLDER,
        "--business_entity",
        business_entity,
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        return f"Error processing files: {str(e)}"

    merged_pdf_path = os.path.join(OUTPUT_FOLDER, f"{business_entity}-PWR-ADDDATE")
    csv_file_path = os.path.join(OUTPUT_FOLDER, f"{business_entity}-PWR-ADDDATE")
    return "Files processed."

from flask import send_file

@app.route('/download')
def download_files():
    business_entity = request.args.get('business_entity')
    csv_path = os.path.join(OUTPUT_FOLDER, f"{business_entity}-PWR-ADDDATE.csv")
    pdf_path = os.path.join(OUTPUT_FOLDER, f"{business_entity}-PWR-ADDDATE.pdf")
    faulty_reports_path = os.path.join(OUTPUT_FOLDER, f"{business_entity}-FAULTYREPORTS-ADDDATE.pdf")

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, mode='w') as z:
        z.write(csv_path, os.path.basename(csv_path))
        z.write(pdf_path, os.path.basename(pdf_path))
        z.write(faulty_reports_path, os.path.basename(faulty_reports_path))
    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='output.zip',
    )

@app.route('/leaderboard')
def leaderboard():
    conn = get_db()
    results = conn.execute('SELECT * FROM results ORDER BY percentage DESC').fetchall()
    conn.close()
    return render_template('leaderboard.html', results=results)

def save_results_to_db(name, score, total_questions, percentage):
    conn = get_db()
    conn.execute('INSERT INTO results (name, score, total_questions, percentage) VALUES (?, ?, ?, ?)',
                 (name, score, total_questions, percentage))
    conn.commit()
    conn.close()

@app.route('/save-results', methods=['POST'])
def save_results():
    name = request.json.get('name')
    score = request.json.get('score')
    total_questions = request.json.get('totalQuestions')
    percentage = request.json.get('percentage')

    conn = sqlite3.connect('./static/exam_results.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO results (name, score, total_questions, percentage) VALUES (?, ?, ?, ?)', (name, score, total_questions, percentage))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Results saved successfully'})

if __name__ == "__main__":
    app.secret_key = 'Is1S3cr3tk3y'
    app.run()
