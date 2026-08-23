from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, flash, jsonify
from .models import User, db, Hatchery, DayOldPrice, State, Category, LGA, Product, Market
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_login import login_required, current_user, login_user, logout_user
from pkg.models import PriceEntry

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def get_admin_user():
    user_id = session.get('useronline')
    if user_id:
        try:
            user_id = int(user_id)
            user = User.query.get(user_id)  # tries by id
            if user:
                return user
            # if that fails, maybe your PK is user_id
            user = User.query.filter_by(user_id=user_id).first()
            if user:
                return user
        except:
            pass
    
    admin_email = session.get('admin_email') or session.get('email') or session.get('user_email')
    if admin_email:
        return User.query.filter_by(email=admin_email).first()
    
    return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login', 'danger')
            return redirect(url_for('admin.login'))
        if not current_user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function



@admin_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Allow initial admin creation if no admin exists; otherwise restrict to logged-in admins
    existing_admin = User.query.filter_by(is_admin=True).first()

    if existing_admin:
        # If there's already an admin, only an authenticated admin can create another
        if 'useronline' not in session:
            flash('Only admins can create new admin accounts', 'danger')
            return redirect(url_for('admin.login'))
        current = User.query.get(session.get('useronline'))
        if not current or not current.is_admin:
            flash('Access denied. Admins only', 'danger')
            return redirect(url_for('admin.login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_pw, is_admin=True)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Admin created successfully', 'success')
            return redirect(url_for('admin.login'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Could not create admin: {exc}', 'danger')
    return render_template('pages/admin_register.html')


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('useronline'):
            current = User.query.get(session.get('useronline'))
            if current and current.is_admin:
                return redirect(url_for('admin.dashboard'))
        return render_template('pages/admin_login.html')

    # POST
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    try:
        user = User.query.filter_by(email=email).first()
    except Exception as exc:
        flash(f'Database error: {exc}', 'danger')
        return redirect(url_for('admin.login'))

    if not user or not check_password_hash(user.password, password):
        flash('Invalid admin credentials', 'danger')
        return redirect(url_for('admin.login'))

    if not user.is_admin:
        flash('This account does not have admin access', 'danger')
        return redirect(url_for('admin.login'))

    login_user(user)  # registers the user with Flask-Login

    session['useronline'] = user.user_id
    session['admin_id'] = user.user_id
    session['admin_email'] = user.email
    session['is_admin'] = bool(user.is_admin)
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/dashboard')
@admin_required 
def dashboard():
    categories = Category.query.order_by(Category.category_name).all()
    return render_template('pages/admin.html', categories=categories)


from flask_login import logout_user

@admin_bp.route('/logout/')
def logout():
    logout_user()  # clears Flask-Login's session state
    session.pop('useronline', None)
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    session.pop('is_admin', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('main.home_page'))

@admin_bp.route('/toggle-hatchery/<int:id>')
@admin_required
def toggle_hatchery(id):
    hatchery = Hatchery.query.get_or_404(id)
    hatchery.is_active = 0 if hatchery.is_active == 1 else 1
    db.session.commit()
    status = "Activated" if hatchery.is_active else "Deactivated"
    flash(f"{hatchery.hatchery_name} {status}")
    return redirect(url_for('admin.manage_hatcheries'))


@admin_bp.route('/manage-hatcheries', methods=['GET', 'POST'])
@admin_required
def manage_hatcheries():
    if request.method == 'POST':
        name = request.form['hatchery_name'].strip()
        contact = request.form['contact'].strip()
        
        if Hatchery.query.filter_by(hatchery_name=name).first():
            flash("Hatchery already exists")
        else:
            new_hatchery = Hatchery(hatchery_name=name, contact=contact)
            db.session.add(new_hatchery)
            db.session.commit()
            flash(f"{name} added successfully")

    hatcheries = Hatchery.query.order_by(Hatchery.hatchery_name).all()
    return render_template('pages/manage_hatcheries.html', hatcheries=hatcheries) 


@admin_bp.route('/edit-hatchery/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_hatchery(id):
    hatchery = Hatchery.query.get_or_404(id)
    
    if request.method == 'POST':
        hatchery.hatchery_name = request.form['hatchery_name'].strip()
        hatchery.contact = request.form['contact'].strip()
        days = request.form.getlist('distribution_days')
        hatchery.distribution_days = ', '.join(days)
        db.session.commit()
        flash(f"{hatchery.hatchery_name} updated successfully", "success")
        return redirect(url_for('admin.manage_hatcheries'))

    return render_template('pages/edit_hatchery.html', hatchery=hatchery)


@admin_bp.route('/delete-hatchery/<int:id>', methods=['POST'])
@admin_required
def delete_hatchery(id):
    hatchery = Hatchery.query.get_or_404(id)
    
    if hatchery.price_entries:
        hatchery.is_active = False
        db.session.commit()
        flash(f"{hatchery.hatchery_name} has price history, so it was deactivated instead of deleted.", "info")
    else:
        db.session.delete(hatchery)
        db.session.commit()
        flash(f"{hatchery.hatchery_name} deleted successfully", "success")
    
    return redirect(url_for('admin.manage_hatcheries'))


@admin_bp.route('/add-day-old', methods=['GET', 'POST'])
@admin_required
def add_day_old():
    if request.method == 'POST':
        try:
            price_date = date.fromisoformat(request.form['price_date'])
        except ValueError:
            flash('Please enter a valid date', 'danger')
            return redirect(url_for('admin.add_day_old'))

        try:
            new_price = DayOldPrice(
                hatchery_id=int(request.form['hatchery_id']),
                bird_type=request.form['bird_type'],
                price=Decimal(request.form['price']),
                availability=request.form['availability'],
                state_id=int(request.form['state_id']),
                price_date=price_date,
                day_of_week=request.form['day_of_week'],
                created_by=int(session['useronline'])
            )
            db.session.add(new_price)
            db.session.commit()
            flash('Day-old price added successfully', 'success')
        except Exception as exc:
            db.session.rollback()
            flash(f'Could not save day-old price: {exc}', 'danger')
            return redirect(url_for('admin.add_day_old'))

        return redirect(url_for('admin.add_day_old'))

    hatcheries = Hatchery.query.filter_by(is_active=1).order_by(Hatchery.hatchery_name).all()
    states = State.query.order_by(State.state_name).all()
    recent_prices = DayOldPrice.query.order_by(DayOldPrice.day_old_id.desc()).limit(10).all()

    return render_template('pages/add_day_old.html', hatcheries=hatcheries, states=states, recent_prices=recent_prices)


@admin_bp.route('/manage-categories', methods=['GET', 'POST'])
@admin_required
def manage_categories():
    if request.method == 'POST':
        name = request.form['name'].strip()
        if Category.query.filter_by(category_name=name).first():
            flash('Category already exists', 'warning')
        else:
            new_cat = Category(category_name=name)
            db.session.add(new_cat)
            db.session.commit()
            flash('Category added', 'success')
        return redirect(url_for('admin.manage_categories')) 
    
    categories = Category.query.order_by(Category.category_name).all()
    return render_template('pages/manage_categories.html', categories=categories)


@admin_bp.route('/edit-category/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        category.category_name = request.form.get('name')
        db.session.commit()
        flash('Category updated successfully', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('pages/edit_category.html', category=category)

@admin_bp.route('/delete-category/<int:id>')
@admin_required
def delete_category(id):
    cat = Category.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Category deleted', 'success')
    return redirect(url_for('admin.manage_categories'))


@admin_bp.route('/prices/')
def view_prices():
    # Get filter values from URL
    state_id = request.args.get('state_id')
    lga_id = request.args.get('lga_id')
    product_id = request.args.get('product_id')

    # IMPORTANT: Only show APPROVED prices
    query = PriceEntry.query.filter_by(is_approved=True)

    if state_id:
        query = query.filter(PriceEntry.state_id == state_id)
    if lga_id:
        query = query.filter(PriceEntry.lga_id == lga_id)
    if product_id:
        query = query.filter(PriceEntry.product_id == product_id)

    prices = query.order_by(PriceEntry.date_submitted.desc()).all()

    # Get data for the dropdowns
    states = State.query.all()
    lgas = LGA.query.all()
    products = Product.query.all()

    return render_template('pages/prices.html', 
                           prices=prices, 
                           states=states, 
                           lgas=lgas, 
                           products=products)


@admin_bp.route('/get-lgas/<int:state_id>')
def get_lgas(state_id):
    lgas = LGA.query.filter_by(state_id=state_id).all()
    lga_list = [{'lga_id': lga.lga_id, 'lga_name': lga.lga_name} for lga in lgas]
    return jsonify(lga_list)


@admin_bp.route('/add-day-old-price', methods=['GET', 'POST'])
@admin_required
def add_day_old_price():
    DAY_OLD_PRODUCT_IDS = [24, 25, 26, 27]  # Broiler, Pullet, Noiler, Turkey Poult

    if request.method == 'POST':
        product_id = request.form['product_id']
        hatchery_id = request.form['hatchery_id']
        state_id = request.form['state_id']
        lga_id = request.form['lga_id']
        price = request.form['price']

        new_price = PriceEntry(
            product_id=product_id,
            hatchery_id=hatchery_id,
            state_id=state_id,
            lga_id=lga_id,
            price=price,
            source_type='Farm',
            submitted_by=current_user.user_id,
            is_approved=True  # admin-submitted, auto-approved
        )
        db.session.add(new_price)
        db.session.commit()
        flash('Day-old price added successfully!', 'success')
        return redirect(url_for('admin.add_day_old_price'))

    day_old_products = Product.query.filter(Product.product_id.in_(DAY_OLD_PRODUCT_IDS)).all()
    hatcheries = Hatchery.query.filter_by(is_active=1).all()
    states = State.query.all()
    today = date.today()
    return render_template(
        'pages/add_day_old_price.html',
        day_old_products=day_old_products,
        hatcheries=hatcheries,
        states=states,
        today=today
    )



@admin_bp.route('/review-prices', methods=['GET'])
@admin_required
def review_prices():
    pending = PriceEntry.query.filter_by(is_approved=False)\
        .order_by(PriceEntry.product_id, PriceEntry.state_id, PriceEntry.lga_id, PriceEntry.date_submitted)\
        .all()

    groups = {}
    for entry in pending:
        key = (entry.product_id, entry.lga_id)
        if key not in groups:
            groups[key] = {
                'product': entry.product,
                'state': entry.state,
                'lga': entry.lga,
                'entries': [],
            }
        groups[key]['entries'].append(entry)

    for key, group in groups.items():
        prices = [float(e.price) for e in group['entries']]
        group['average'] = sum(prices) / len(prices)
        group['count'] = len(prices)

    return render_template('pages/review_prices.html', groups=groups.values())


@admin_bp.route('/approve-group', methods=['POST'])
@admin_required
def approve_group():
    entry_ids = request.form.getlist('entry_ids')
    if entry_ids:
        PriceEntry.query.filter(PriceEntry.id.in_(entry_ids)).update(
            {PriceEntry.is_approved: True}, synchronize_session=False
        )
        db.session.commit()
        flash(f'{len(entry_ids)} price entries approved', 'success')
    else:
        flash('No entries selected', 'warning')
    return redirect(url_for('admin.review_prices'))


@admin_bp.route('/reject-entry/<int:entry_id>', methods=['POST'])
@admin_required
def reject_entry(entry_id):
    entry = PriceEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry rejected and removed', 'info')
    return redirect(url_for('admin.review_prices'))
