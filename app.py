from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Load environment variables from .env file
load_dotenv()

# Configuration settings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Suggest using an environment variable for SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///car_audio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# Initialize database and migration tools
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Set up Flask-Login for user session management
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model representing a system user (e.g., admin, salesperson)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    # Hash the password before saving
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # Verify the password during login
    def check_password(self, password):
        return check_password_hash(self.password, password)

# Load the current user from the session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Customer model storing customer details
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)
    appointments = db.relationship('Appointment', backref='customer', lazy=True)
    comments = db.Column(db.Text)

# Vehicle model representing a customer's vehicle
class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    appointments = db.relationship('Appointment', backref='vehicle', lazy=True)

# Product model storing product details related to installations
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    serial_number = db.Column(db.String(100))
    warranty_info = db.Column(db.String(100))
    appointments = db.relationship('Appointment', back_populates='product', lazy=True)

# Installer model representing an installer with associated skill level
class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    skill_level = db.Column(db.String(50), nullable=False)
    appointments = db.relationship('Appointment', back_populates='installer', lazy=True)

# Appointment model representing an installation appointment
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    installer_id = db.Column(db.Integer, db.ForeignKey('installer.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    install_type = db.Column(db.String(50), nullable=False)
    comments = db.Column(db.Text)

    product = db.relationship('Product', back_populates='appointments', lazy=True)
    installer = db.relationship('Installer', back_populates='appointments', lazy=True)
    installation_jobs = db.relationship('InstallationJob', back_populates='appointment', lazy=True)

# InstallationJob model storing details about specific installation tasks within an appointment
class InstallationJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_details = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)

    appointment = db.relationship('Appointment', back_populates='installation_jobs', lazy=True)

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            message = "Username already exists"
        else:
            # Create and save new user
            new_user = User(username=username, role=role.capitalize())
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            message = "User Created Successfully"
    
    return render_template('register.html', message=message)

# Route for user login with role-based redirection
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        # Validate user credentials and role
        if user and user.check_password(password) and user.role == role.capitalize():
            login_user(user)
            return redirect(url_for(f'{role}_dashboard'))
        else:
            return "Invalid username, password, or role"
    
    return render_template(f'login_{role}.html')

# Route for user logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# General dashboard accessible after login
@app.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome {current_user.username}! You are logged in as {current_user.role}."

# Route for Sales Dashboard
@app.route('/sales_dashboard')
@login_required
def sales_dashboard():
    return "Welcome to the Sales Dashboard!"

# Route for Installation Dashboard
@app.route('/installation_dashboard')
@login_required
def installation_dashboard():
    return "Welcome to the Installation Dashboard!"

# Manager-specific dashboard with user and appointment management
@app.route('/manager_dashboard', methods=['GET', 'POST'])
@login_required
def manager_dashboard():
    if current_user.role != 'Manager':
        return "Access Denied", 403
    
    users = User.query.all()
    customers = Customer.query.all()
    appointments = Appointment.query.all()

    if request.method == 'POST':
        handle_manager_form_submission(request.form)
        return redirect(url_for('manager_dashboard'))

    return render_template('manager_dashboard.html', users=users, customers=customers, appointments=appointments)

# Handle form submissions on the manager dashboard
def handle_manager_form_submission(form_data):
    if 'add_user' in form_data:
        add_user(form_data)
    elif 'update_user' in form_data:
        update_user(form_data)
    elif 'delete_customer' in form_data:
        delete_customer(form_data)
    elif 'delete_appointment' in form_data:
        delete_appointment_entry(form_data)
    elif 'delete_user' in form_data:
        delete_user(form_data)

# Add a new user to the database
def add_user(form_data):
    username = form_data.get('username')
    password = form_data.get('password')
    role = form_data.get('role')
    new_user = User(username=username, role=role.capitalize())
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

# Update existing user information
def update_user(form_data):
    user_id = form_data.get('user_id')
    user = User.query.get(user_id)
    new_password = form_data.get('new_password')
    new_email = form_data.get('new_email')
    if new_password:
        user.set_password(new_password)
    if new_email:
        user.email = new_email
    db.session.commit()

# Delete a customer from the database
def delete_customer(form_data):
    customer_id = form_data.get('customer_id')
    customer = Customer.query.get(customer_id)
    db.session.delete(customer)
    db.session.commit()

# Delete an appointment from the database
def delete_appointment_entry(form_data):
    appointment_id = form_data.get('appointment_id')
    appointment = Appointment.query.get(appointment_id)
    db.session.delete(appointment)
    db.session.commit()

# Delete a user from the database
def delete_user(form_data):
    user_id = form_data.get('user_id')
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()

# Route for the main index page
@app.route('/')
def index():
    return render_template('index.html')

# Route for scheduling appointments
@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    if request.method == 'POST':
        if not process_appointment_form(request.form):
            return "There was an issue saving the appointment", 500
        return redirect(url_for('schedule'))

    events = retrieve_calendar_events()
    return render_template('schedule.html', events=events)

# Process the form data and create a new appointment
def process_appointment_form(form_data):
    try:
        start_time, end_time = calculate_appointment_times(form_data)
        customer = get_or_create_customer(form_data)
        vehicle = get_or_create_vehicle(form_data, customer)
        product = get_or_create_product(form_data)

        # Create a new appointment record
        new_appointment = create_appointment(start_time, end_time, customer, vehicle, product, form_data)
        db.session.add(new_appointment)
        db.session.commit()  # Commit to generate the new_appointment.id

        # Create associated installation jobs
        create_installation_jobs(form_data, new_appointment)
        db.session.commit()

        return True
    except Exception as e:
        db.session.rollback()  # Rollback changes on error
        app.logger.error(f'Error saving appointment: {e}')
        return False

# Calculate start and end times for an appointment based on form data
def calculate_appointment_times(form_data):
    start_time = form_data.get('start_time')
    duration_str = form_data.get('duration')
    
    if not duration_str:
        raise ValueError("Duration is required")

    try:
        duration = int(duration_str)
    except ValueError:
        raise ValueError("Invalid duration value")

    start_time = datetime.fromisoformat(start_time)  # Keep this as naive datetime
    end_time = start_time + timedelta(hours=duration)
    return start_time, end_time

# Retrieve or create a new customer based on form data
def get_or_create_customer(form_data):
    # Always create a new customer based on the form data, regardless of phone number
    customer = Customer(
        first_name=form_data.get('customer_first_name'),
        last_name=form_data.get('customer_last_name'),
        phone_number=form_data.get('customer_phone')
    )
    db.session.add(customer)
    db.session.commit()

    return customer

# Retrieve or create a vehicle associated with a customer
def get_or_create_vehicle(form_data, customer):
    vehicle_year = form_data.get('vehicle_year')
    vehicle_make = form_data.get('vehicle_make')
    vehicle_model = form_data.get('vehicle_model')

    vehicle = Vehicle.query.filter_by(year=vehicle_year, make=vehicle_make, model=vehicle_model, customer_id=customer.id).first()
    if not vehicle:
        vehicle = Vehicle(
            year=vehicle_year,
            make=vehicle_make,
            model=vehicle_model,
            customer_id=customer.id
        )
        db.session.add(vehicle)
        db.session.commit()

    return vehicle

# Retrieve or create a product associated with an appointment
def get_or_create_product(form_data):
    product_name = form_data.get('product_name[]')  # Assuming a single product
    product_price = form_data.get('product_price[]')

    product = Product.query.filter_by(name=product_name).first()
    if not product:
        product = Product(
            name=product_name,
            price=float(product_price) if product_price else 0.0,
            type=form_data.get('installation_type')
        )
        db.session.add(product)
        db.session.commit()

    return product

# Create a new appointment record in the database
def create_appointment(start_time, end_time, customer, vehicle, product, form_data):
    return Appointment(
        start_time=start_time,  # Use naive datetime
        end_time=end_time,      # Use naive datetime
        customer_id=customer.id,
        vehicle_id=vehicle.id,
        product_id=product.id,
        install_type=form_data.get('installation_type'),
        comments=form_data.get('notes')
    )

# Create installation job records associated with an appointment
def create_installation_jobs(form_data, new_appointment):
    installation_jobs = form_data.getlist('installation_job[]')
    installation_prices = form_data.getlist('installation_price[]')

    for job_details, price in zip(installation_jobs, installation_prices):
        installation_job = InstallationJob(
            job_details=job_details,
            price=float(price),
            appointment_id=new_appointment.id
        )
        db.session.add(installation_job)


@app.route('/events')
def events():
    try:
        events = retrieve_calendar_events()  # Assuming this function retrieves and formats your events
        return jsonify(events)
    except Exception as e:
        app.logger.error(f"Error retrieving events: {e}")
        return jsonify({'status': 'error', 'message': 'Could not retrieve events'}), 500


# Retrieve all appointments and prepare them for display on a calendar
def retrieve_calendar_events():
    appointments = Appointment.query.all()
    events = []
    for appointment in appointments:
        events.append({
            'id': appointment.id,
            'title': f'{appointment.customer.first_name} {appointment.customer.last_name} - {appointment.product.name}',
            'start': appointment.start_time.isoformat(),
            'end': appointment.end_time.isoformat(),
            'color': 'blue' if appointment.install_type == 'standard' else 'orange',
            'extendedProps': {
                'customer_first_name': appointment.customer.first_name,
                'customer_last_name': appointment.customer.last_name,
                'customer_phone': appointment.customer.phone_number,
                'vehicle_year': appointment.vehicle.year,
                'vehicle_make': appointment.vehicle.make,
                'vehicle_model': appointment.vehicle.model,
                'installation_type': appointment.install_type,
                'duration': (appointment.end_time - appointment.start_time).seconds // 3600,
                'notes': appointment.comments,
                'installation_jobs': [{'job_details': job.job_details, 'price': job.price} for job in appointment.installation_jobs]
            }
        })
    return events

# Route to delete an appointment
@app.route('/appointment/delete/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    if appointment:
        # Optionally delete related installation jobs manually if cascade isn't configured
        db.session.query(InstallationJob).filter_by(appointment_id=appointment.id).delete()
        
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Appointment deleted successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Appointment not found'}), 404

# Route to edit an existing appointment
@app.route('/appointment/edit/<int:appointment_id>', methods=['POST'])
@login_required
def edit_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    
    if appointment:
        try:
            # Update start and end times
            start_time = request.form.get('start_time')
            duration_str = request.form.get('duration')
            if not start_time or not duration_str:
                return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
            
            duration = int(duration_str)
            appointment.start_time = datetime.fromisoformat(start_time)
            appointment.end_time = appointment.start_time + timedelta(hours=duration)

            # Update vehicle information
            vehicle_year = request.form.get('vehicle_year')
            vehicle_make = request.form.get('vehicle_make')
            vehicle_model = request.form.get('vehicle_model')
            if vehicle_year and vehicle_make and vehicle_model:
                vehicle = appointment.vehicle
                vehicle.year = vehicle_year
                vehicle.make = vehicle_make
                vehicle.model = vehicle_model

            # Update installation type and notes
            appointment.install_type = request.form.get('installation_type')
            appointment.comments = request.form.get('notes')

            # Update installation jobs
            existing_jobs = {job.id: job for job in appointment.installation_jobs}
            form_job_ids = request.form.getlist('installation_job_id[]')
            form_job_details = request.form.getlist('edit_installation_job[]')
            form_job_prices = request.form.getlist('edit_installation_price[]')

            # Remove jobs not in form
            for job_id in existing_jobs:
                if str(job_id) not in form_job_ids:
                    db.session.delete(existing_jobs[job_id])

            # Add or update jobs
            for idx, job_id in enumerate(form_job_ids):
                job_details = form_job_details[idx]
                job_price = form_job_prices[idx]
                if job_id:
                    # Update existing job
                    job = existing_jobs.get(int(job_id))
                    if job:
                        job.job_details = job_details
                        job.price = float(job_price)
                else:
                    # Create new job
                    new_job = InstallationJob(
                        job_details=job_details,
                        price=float(job_price),
                        appointment_id=appointment.id
                    )
                    db.session.add(new_job)

            db.session.commit()
            print('success')
            return jsonify({'status': 'success', 'message': 'Appointment updated successfully'})
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error editing appointment: {e}')
            return jsonify({'status': 'error', 'message': 'Error editing appointment'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Appointment not found'}), 404

# Route to move an appointment to a new time
@app.route('/appointment/move/<int:appointment_id>', methods=['POST'])
@login_required
def move_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if appointment:
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        if not start_time or not end_time:
            return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
        
        try:
            # Parse the ISO format datetime strings to Python datetime objects
            start_time_dt = datetime.fromisoformat(start_time)
            end_time_dt = datetime.fromisoformat(end_time)
            
            # Update the appointment's start and end times
            appointment.start_time = start_time_dt
            appointment.end_time = end_time_dt

            db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error moving appointment: {e}')
            return jsonify({'status': 'error', 'message': 'Error moving appointment'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Appointment not found'}), 404


# Function to print all products, along with associated customer and vehicle, on app startup
def print_products_on_startup():
    products = Product.query.all()
    if products:
        print("Products in the database:")
        for product in products:
            print(f'Product Name: {product.name}, Price: {product.price}, Type: {product.type}')
            
            # Loop through the associated appointments
            for appointment in product.appointments:
                customer = appointment.customer
                vehicle = appointment.vehicle
                
                if customer:
                    print(f'  Customer Name: {customer.first_name} {customer.last_name}, Phone: {customer.phone_number}')
                else:
                    print("  No customer associated with this product.")
                
                if vehicle:
                    print(f'  Vehicle: {vehicle.year} {vehicle.make} {vehicle.model}')
                else:
                    print("  No vehicle associated with this product.")
    else:
        print("No products found in the database.")
  


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    with app.app_context():
        db.create_all()

        print_products_on_startup()


        # Query and print appointment start and end times
        appointments = Appointment.query.all()
        if appointments:
            for appointment in appointments:
                print(f'Appointment ID: {appointment.id}, Start time: {appointment.start_time}, End time: {appointment.end_time}')
        else:
            print('No appointments found in the database.')

    
        

        app.run(debug=True)
