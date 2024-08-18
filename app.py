from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session
from datetime import timedelta
from flask_migrate import Migrate

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
    with Session(db.engine) as session:
        return session.get(User, int(user_id))

# Customer table
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)
    appointments = db.relationship('Appointment', backref='customer', lazy=True)
    comments = db.Column(db.Text)

# Vehicle table
class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    appointments = db.relationship('Appointment', backref='vehicle', lazy=True)

# Product table
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    serial_number = db.Column(db.String(100))
    warranty_info = db.Column(db.String(100))

# Installer table
class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    skill_level = db.Column(db.String(50), nullable=False)
    appointments = db.relationship('Appointment', backref='installer', lazy=True)

# Modify the Appointment table to include end_time
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)  # Rename 'date' to 'start_time'
    end_time = db.Column(db.DateTime, nullable=False)  # New column to store end time
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    installer_id = db.Column(db.Integer, db.ForeignKey('installer.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    install_type = db.Column(db.String(50), nullable=False)
    comments = db.Column(db.Text)

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

# Example protected route
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
        # Handle form submissions for adding or updating users, deleting customers, or deleting appointments

        # Add new user
        if 'add_user' in request.form:
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')
            new_user = User(username=username, role=role.capitalize())
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

        # Update user (password or email)
        if 'update_user' in request.form:
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            new_password = request.form.get('new_password')
            new_email = request.form.get('new_email')
            if new_password:
                user.set_password(new_password)
            if new_email:
                user.email = new_email
            db.session.commit()

        # Delete customer
        if 'delete_customer' in request.form:
            customer_id = request.form.get('customer_id')
            customer = Customer.query.get(customer_id)
            db.session.delete(customer)
            db.session.commit()

        # Delete appointment
        if 'delete_appointment' in request.form:
            appointment_id = request.form.get('appointment_id')
            appointment = Appointment.query.get(appointment_id)
            db.session.delete(appointment)
            db.session.commit()

        # Delete user
        if 'delete_user' in request.form:
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            db.session.delete(user)
            db.session.commit()

        return redirect(url_for('manager_dashboard'))

    return render_template('manager_dashboard.html', users=users, customers=customers, appointments=appointments)


@app.route('/')
def index():
    return render_template('index.html')


from datetime import datetime

@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        vehicle_id = request.form.get('vehicle_id')
        product_id = request.form.get('product_id')
        install_type = request.form.get('installation_type')
        start_time = request.form.get('start_time')
        duration = int(request.form.get('duration'))
        end_time = datetime.fromisoformat(start_time) + timedelta(hours=duration)
        comments = request.form.get('comments', '')

        if not all([customer_id, vehicle_id, product_id, install_type, start_time]):
            return "Missing data for appointment creation", 400

        new_appointment = Appointment(
            date=start_time,
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            product_id=product_id,
            install_type=install_type,
            comments=comments
        )
        db.session.add(new_appointment)
        db.session.commit()

        return redirect(url_for('schedule'))

    # Handle GET requests - return appointments in JSON format
    appointments = Appointment.query.all()
    events = []
    for appointment in appointments:
        events.append({
            'title': f'{appointment.customer.first_name} {appointment.customer.last_name} - {appointment.install_type}',
            'start': appointment.date.isoformat(),
            'end': (appointment.date + timedelta(hours=appointment.duration)).isoformat(),
            'color': 'blue' if appointment.install_type == 'standard' else 'orange'
        })

    return render_template('schedule.html', events=events)





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
