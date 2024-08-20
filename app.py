from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from flask_migrate import Migrate
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your actual secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///car_audio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Customer model
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)
    appointments = db.relationship('Appointment', backref='customer', lazy=True)
    comments = db.Column(db.Text)

# Vehicle model
class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    appointments = db.relationship('Appointment', backref='vehicle', lazy=True)

# Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    serial_number = db.Column(db.String(100))
    warranty_info = db.Column(db.String(100))
    appointments = db.relationship('Appointment', back_populates='product', lazy=True)

# Installer model
class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    skill_level = db.Column(db.String(50), nullable=False)
    appointments = db.relationship('Appointment', back_populates='installer', lazy=True)

# Appointment model
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

# InstallationJob model
class InstallationJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_details = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)

    appointment = db.relationship('Appointment', back_populates='installation_jobs', lazy=True)

# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            message = "Username already exists"
        else:
            new_user = User(username=username, role=role.capitalize())
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            message = "User Created Successfully"
    
    return render_template('register.html', message=message)

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.role == role.capitalize():
            login_user(user)
            return redirect(url_for(f'{role}_dashboard'))
        else:
            return "Invalid username, password, or role"
    
    return render_template(f'login_{role}.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome {current_user.username}! You are logged in as {current_user.role}."

@app.route('/sales_dashboard')
@login_required
def sales_dashboard():
    return "Welcome to the Sales Dashboard!"

@app.route('/installation_dashboard')
@login_required
def installation_dashboard():
    return "Welcome to the Installation Dashboard!"

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

def add_user(form_data):
    username = form_data.get('username')
    password = form_data.get('password')
    role = form_data.get('role')
    new_user = User(username=username, role=role.capitalize())
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

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

def delete_customer(form_data):
    customer_id = form_data.get('customer_id')
    customer = Customer.query.get(customer_id)
    db.session.delete(customer)
    db.session.commit()

def delete_appointment_entry(form_data):
    appointment_id = form_data.get('appointment_id')
    appointment = Appointment.query.get(appointment_id)
    db.session.delete(appointment)
    db.session.commit()

def delete_user(form_data):
    user_id = form_data.get('user_id')
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    if request.method == 'POST':
        if not process_appointment_form(request.form):
            return "There was an issue saving the appointment", 500
        return redirect(url_for('schedule'))

    events = retrieve_calendar_events()
    return render_template('schedule.html', events=events)

def process_appointment_form(form_data):
    try:
        start_time, end_time = calculate_appointment_times(form_data)
        customer = get_or_create_customer(form_data)
        vehicle = get_or_create_vehicle(form_data, customer)
        product = get_or_create_product(form_data)

        new_appointment = create_appointment(start_time, end_time, customer, vehicle, product, form_data)
        db.session.add(new_appointment)
        db.session.commit()  # Commit to generate the new_appointment.id

        create_installation_jobs(form_data, new_appointment)
        db.session.commit()

        return True
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error saving appointment: {e}')
        return False

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

def get_or_create_customer(form_data):
    customer_phone = form_data.get('customer_phone')
    customer = Customer.query.filter_by(phone_number=customer_phone).first()

    if not customer:
        customer = Customer(
            first_name=form_data.get('customer_first_name'),
            last_name=form_data.get('customer_last_name'),
            phone_number=customer_phone
        )
        db.session.add(customer)
        db.session.commit()

    return customer

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


@app.route('/appointment/edit/<int:appointment_id>', methods=['POST'])
@login_required
def edit_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    
    if appointment:
        try:
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            app.logger.debug(f"Received times: Start Time: {start_time}, End Time: {end_time}")
            # Log the initial state
            app.logger.debug(f'Editing appointment ID: {appointment_id}, Initial data: {appointment}')

            # Update start and end times
            start_time = request.form.get('start_time')
            duration_str = request.form.get('duration')
            if not start_time or not duration_str:
                return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
            
            duration = int(duration_str)
            appointment.start_time = datetime.fromisoformat(start_time)  # Naive datetime
            appointment.end_time = appointment.start_time + timedelta(hours=duration)
            
            # Log the updated times
            app.logger.debug(f'Updated start time: {appointment.start_time}, end time: {appointment.end_time}')

            # Update customer information
            customer_first_name = request.form.get('customer_first_name')
            customer_last_name = request.form.get('customer_last_name')
            customer_phone = request.form.get('customer_phone')
            if customer_first_name and customer_last_name and customer_phone:
                customer = appointment.customer
                customer.first_name = customer_first_name
                customer.last_name = customer_last_name
                customer.phone_number = customer_phone
            
            # Log customer update
            app.logger.debug(f'Updated customer: {customer}')

            # Update vehicle information
            vehicle_year = request.form.get('vehicle_year')
            vehicle_make = request.form.get('vehicle_make')
            vehicle_model = request.form.get('vehicle_model')
            if vehicle_year and vehicle_make and vehicle_model:
                vehicle = appointment.vehicle
                vehicle.year = vehicle_year
                vehicle.make = vehicle_make
                vehicle.model = vehicle_model

            # Log vehicle update
            app.logger.debug(f'Updated vehicle: {vehicle}')

            # Update installation type and notes
            installation_type = request.form.get('installation_type')
            notes = request.form.get('notes')
            appointment.install_type = installation_type
            appointment.comments = notes

            # Update installation jobs
            installation_jobs = request.form.getlist('edit_installation_job[]')
            installation_prices = request.form.getlist('edit_installation_price[]')
            existing_jobs = appointment.installation_jobs

            # Log installation jobs before update
            app.logger.debug(f'Existing jobs before update: {existing_jobs}')

            # Remove existing jobs that are no longer in the form
            job_ids_in_form = {int(job_id) for job_id in request.form.getlist('installation_job_id[]')}
            jobs_to_remove = [job for job in existing_jobs if job.id not in job_ids_in_form]
            for job in jobs_to_remove:
                db.session.delete(job)

            # Log jobs to remove
            app.logger.debug(f'Jobs to remove: {jobs_to_remove}')
            
            # Update existing jobs and add new ones
            for job_details, price in zip(installation_jobs, installation_prices):
                if job_details and price:
                    job = next((job for job in existing_jobs if job.job_details == job_details), None)
                    if job:
                        job.job_details = job_details
                        job.price = float(price)
                    else:
                        new_job = InstallationJob(
                            job_details=job_details,
                            price=float(price),
                            appointment_id=appointment.id
                        )
                        db.session.add(new_job)

            # Log after update
            app.logger.debug(f'Appointment after update: {appointment}')
            
            db.session.commit()
            # Redirect to the schedule page after successful update
            return redirect(url_for('schedule'))
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error editing appointment: {e}')
            return jsonify({'status': 'error', 'message': 'Error editing appointment'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Appointment not found'}), 404

@app.route('/appointment/move/<int:appointment_id>', methods=['POST'])
@login_required
def move_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if appointment:
        start_time = request.form.get('start_time')
        if not start_time:
            return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
        
        try:
            appointment.start_time = datetime.fromisoformat(start_time)  # Naive datetime
            appointment.end_time = appointment.start_time + (appointment.end_time - appointment.start_time)
            db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error moving appointment: {e}')
            return jsonify({'status': 'error', 'message': 'Error moving appointment'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Appointment not found'}), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Query and print appointment start and end times
        appointments = Appointment.query.all()
        if appointments:
            for appointment in appointments:
                print(f'Appointment ID: {appointment.id}, Start time: {appointment.start_time}, End time: {appointment.end_time}')
        else:
            print('No appointments found in the database.')

        app.run(debug=True)
