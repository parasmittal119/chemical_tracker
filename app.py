from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode
import os
import pandas as pd
import io
from sqlalchemy import inspect, text
import getpass

# Initialize Flask app
app = Flask(__name__)
db_path = r'D:\test\Programs\Base Codes\Chemical_validation\instance\chemicals.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Ensure the necessary directories exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'static/qr_codes'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

# Define the Chemical model
class Chemical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vendor = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    material = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    register_time = db.Column(db.DateTime, nullable=False)
    qr_code = db.Column(db.String(100), nullable=False)


class Scanned_barcode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

# Load Excel data
def load_excel_data():
    # Define the path to the Excel file
    excel_path = os.path.join(os.path.dirname(__file__), 'data', 'master.xlsx')
    # Read the Excel file
    df = pd.read_excel(excel_path)
    # Create a dictionary mapping descriptions to vendors
    description_to_vendor = df.set_index('Description')['Supplier'].to_dict()
    # Create a dictionary mapping descriptions to materials
    description_to_material = df.set_index('Description')['Material'].to_dict()
    # Extract unique descriptions
    descriptions = df['Description'].unique().tolist()
    return descriptions, description_to_vendor, description_to_material

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

# Register page route
@app.route('/register')
def register():
    descriptions, description_to_vendor, description_to_material = load_excel_data()
    return render_template('register.html', descriptions=descriptions)

# Endpoint to get vendor and material based on description
@app.route('/get-info', methods=['GET'])
def get_info():
    description = request.args.get('description')
    descriptions, description_to_vendor, description_to_material = load_excel_data()
    vendor = description_to_vendor.get(description, '')
    material = description_to_material.get(description, '')
    return jsonify(vendor=vendor, material=material)

# Save chemical route
@app.route('/save-chemical', methods=['POST'])
def save_chemical():
    data = request.get_json()
    manufacturing_date = datetime.strptime(data['manufacturing_date'], '%Y-%m-%d')
    expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
    
    # Get current timestamp
    current_time = datetime.now()

    # Concatenate chemical information with underscores as delimiters
    qr_code_data = '_'.join([
        data['name'],
        data['vendor'],
        data['description'],
        data['material'],
        data['manufacturing_date'],
        data['expiry_date']
    ])

    # Generate QR code
    qr = qrcode.make(qr_code_data)
    
    # Format date strings for filename
    formatted_manufacturing_date = manufacturing_date.strftime('%Y-%m-%d')
    formatted_expiry_date = expiry_date.strftime('%Y-%m-%d')
    
    qr_code_filename = f"{data['material']}_{formatted_manufacturing_date}_{formatted_expiry_date}.png"
    downloads_folder = os.path.join("C:", "Users", getpass.getuser(), "Downloads")
    qr_file_path = os.path.join(downloads_folder, qr_code_filename)
    qr.save(qr_file_path)

    # Save chemical information to the database
    chemical = Chemical(
        name=data['name'],
        vendor=data['vendor'],
        description=data['description'],
        material=data['material'],
        manufacturing_date=manufacturing_date,
        expiry_date=expiry_date,
        qr_code=qr_code_filename,
        register_time=current_time  # Adding current timestamp
    )
    db.session.add(chemical)
    db.session.commit()

    return jsonify(message="Chemical registered successfully!")

# Validation page route
@app.route('/validate')
def validate():
    return render_template('validate.html')

# Flask route to handle barcode submission and redirect to validation result page
@app.route('/validate-chemical', methods=['POST'])
def validate_chemical():
    barcode = request.form['barcode']
    print(barcode)
    manufacturing_date = barcode.split("_")[-1]
    chemical = Chemical.query.filter_by(expiry_date=manufacturing_date).first()
    message = []
    barcode_scanned = Scanned_barcode(barcode=barcode, timestamp=datetime.now())
    db.session.add(barcode_scanned)
    db.session.commit()
    if chemical:
        today = datetime.today().date()
        if today <= chemical.expiry_date:
            message.append("OK to Use!")
        else:
            message.append("Material has expired, NOT OK to use!")
        message.append(chemical.description)
        message.append(chemical.expiry_date)
    else:
        message.append("Material not found in database")
        message.append("")
        message.append("")
        
    return render_template('validation_result.html', message=message)

# Download page route
@app.route('/download')
def download():
    inspector = inspect(db.engine)
    available_tables = inspector.get_table_names()
    return render_template('download.html', tables=available_tables)

# Fetch table content based on user selection
@app.route('/get-table-content')
def get_table_content():
    table_name = request.args.get('table')
    if table_name:
        with db.engine.connect() as connection:
            result = connection.execute(text(f'SELECT * FROM {table_name} ORDER BY id'))  # Ensure ordering by the primary key or a specific column
            rows = result.fetchall()
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in rows]
        return jsonify(data=data, columns=columns)
    return jsonify(data=[], columns=[])

# Download the selected table as an Excel file
@app.route('/download-excel')
def download_excel():
    table_name = request.args.get('table')
    if table_name:
        with db.engine.connect() as connection:
            result = connection.execute(text(f'SELECT * FROM {table_name} ORDER BY id'))  # Ensure ordering by the primary key or a specific column
            rows = result.fetchall()
            columns = result.keys()
            df = pd.DataFrame(rows, columns=columns)
            
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name=table_name)
            writer.close()  # Use close() instead of save()
            output.seek(0)
            
            return send_file(output, download_name=f'{table_name}.xlsx', as_attachment=True)
    return redirect(url_for('download'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")