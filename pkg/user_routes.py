from datetime import datetime
from decimal import Decimal
from flask_login import login_required, current_user, logout_user, login_user
from flask import Blueprint, render_template, url_for, redirect, request, flash, session, jsonify

from werkzeug.security import generate_password_hash, check_password_hash

from pkg.models import db, User, State, LGA, Category, Product, DayOldPrice, PriceEntry
from pkg.forms import LoginForm


user_bp = Blueprint('main', __name__)


@user_bp.route('/')
def home_page():
    return render_template('user/index.html')


@user_bp.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.home_page'))
        return render_template('user/login.html', form=form)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        try:
            user = User.query.filter_by(email=email).first()
        except Exception as exc:
            flash(f'Database error: {exc}', category='errormsg')
            return redirect(url_for('main.login'))

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['useronline'] = user.user_id
            flash('Welcome back!', category='feedback')
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.home_page'))

        flash('Invalid email or password', category='errormsg')
        return redirect(url_for('main.login'))

    return render_template('user/login.html', form=form)


@user_bp.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        states = State.query.all()
        return render_template('user/register.html', states=states)

    username = request.form.get('username', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm_pass = request.form.get('confirm_pass', '')
    state_id = request.form.get('state', '').strip()

    if not username or not phone or not email or not password or not state_id:
        flash('All fields are required', category='errormsg')
        return redirect(url_for('main.register'))

    if password != confirm_pass:
        flash('The two passwords must match', category='errormsg')
        return redirect(url_for('main.register'))

    try:
        existing_user = User.query.filter_by(email=email).first()
    except Exception as exc:
        flash(f'Database error: {exc}', category='errormsg')
        return redirect(url_for('main.register'))

    if existing_user:
        flash('An account with that email already exists', category='errormsg')
        return redirect(url_for('main.register'))

    try:
        user = User(
            username=username,
            phone_number=phone,
            email=email,
            state_id=int(state_id),
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully', category='feedback')
        return redirect(url_for('main.login'))
    except Exception as exc:
        db.session.rollback()
        flash(f'Error creating account: {exc}', category='errormsg')
        return redirect(url_for('main.register'))

from sqlalchemy import func

@user_bp.route('/dashboard/')
def dashboard():
    current_prices = db.session.query(
        Product.product_name,
        func.avg(PriceEntry.price).label('avg_price')
    ).join(PriceEntry, PriceEntry.product_id == Product.product_id)\
     .filter(PriceEntry.is_approved == True)\
     .group_by(Product.product_id, Product.product_name)\
     .order_by(Product.product_name)\
     .all()

    top_locations = db.session.query(
        State.state_name,
        func.count(PriceEntry.id)
    ).join(PriceEntry, PriceEntry.state_id == State.state_id)\
     .filter(PriceEntry.is_approved == True)\
     .group_by(State.state_id, State.state_name)\
     .order_by(func.count(PriceEntry.id).desc())\
     .limit(5).all()

    return render_template('user/dashboard.html',
                           current_prices=current_prices,
                           top_locations=top_locations)

@user_bp.route('/prices/')
def prices():
    excluded_states = {'Abuja', 'Federal Capital Territory', 'Federal Capital Territory (FCT)'}
    states = State.query.filter(~State.state_name.in_(excluded_states)).order_by(State.state_name).all()
    products = Product.query.order_by(Product.product_name).all()

    state_id = request.args.get('state', type=int)
    lga_id = request.args.get('lga', type=int)
    product_id = request.args.get('product', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    show_all = request.args.get('show_all')  # '1' means show full history, not just latest

    base_query = PriceEntry.query.filter_by(is_approved=True)\
        .join(LGA, PriceEntry.lga_id == LGA.lga_id)\
        .join(Product, PriceEntry.product_id == Product.product_id)\
        .outerjoin(State, PriceEntry.state_id == State.state_id)

    if state_id:
        base_query = base_query.filter(LGA.state_id == state_id)
    if lga_id:
        base_query = base_query.filter(PriceEntry.lga_id == lga_id)
    if product_id:
        base_query = base_query.filter(PriceEntry.product_id == product_id)

    if from_date:
        base_query = base_query.filter(PriceEntry.date_submitted >= from_date)
    if to_date:
        base_query = base_query.filter(PriceEntry.date_submitted <= to_date + ' 23:59:59')

    if show_all == '1' or from_date or to_date:
        price_results = base_query.order_by(PriceEntry.date_submitted.desc()).all()
    else:
        subq = base_query.with_entities(
            PriceEntry.product_id,
            PriceEntry.lga_id,
            func.max(PriceEntry.date_submitted).label('max_date')
        ).group_by(PriceEntry.product_id, PriceEntry.lga_id).subquery()

        price_results = PriceEntry.query.join(
            subq,
            (PriceEntry.product_id == subq.c.product_id) &
            (PriceEntry.lga_id == subq.c.lga_id) &
            (PriceEntry.date_submitted == subq.c.max_date)
        ).order_by(PriceEntry.date_submitted.desc()).all()

    return render_template('user/prices.html',
                          states=states,
                          products=products,
                          prices=price_results,
                          state_id=state_id,
                          lga_id=lga_id,
                          product_id=product_id,
                          from_date=from_date,
                          to_date=to_date,
                          show_all=show_all)


@user_bp.route('/submit/')
def submit():
    DAY_OLD_PRODUCT_IDS = [24, 25, 26, 27]

    excluded_states = {'Abuja', 'Federal Capital Territory', 'Federal Capital Territory (FCT)'}
    states = State.query.filter(~State.state_name.in_(excluded_states)).order_by(State.state_name).all()
    categories = Category.query.order_by(Category.category_name).all()
    try:
        products = Product.query.filter(~Product.product_id.in_(DAY_OLD_PRODUCT_IDS)).order_by(Product.product_name).all()
    except Exception:
        products = []

    lgas_by_state = {}
    for state in states:
        lgas = LGA.query.filter_by(state_id=state.state_id).order_by(LGA.lga_name).all()
        lgas_by_state[str(state.state_id)] = [{'lga_id': lga.lga_id, 'name': lga.lga_name} for lga in lgas]

    return render_template('user/submit.html', states=states, lgas_by_state=lgas_by_state, categories=categories, products=products)


@user_bp.route('/submit-price', methods=['POST'])
@login_required
def submit_price():
    try:
        lga_id = request.form.get('lga_id')
        if not lga_id or lga_id == 'undefined':
            flash('Please select a valid LGA', 'danger')
            return redirect(url_for('main.submit'))

        new_price = PriceEntry(
            product_id = request.form.get('product_id'),
            price = request.form.get('price'),
            state_id = request.form.get('state_id'),
            lga_id = lga_id,
            notes = request.form.get('notes'),
            submitted_by = current_user.user_id,
            date_submitted = datetime.now(),
            is_approved = 0
        )
        db.session.add(new_price)
        db.session.commit()
        flash('Price submitted successfully', 'success')
        return redirect(url_for('main.my_submissions'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {e}', 'danger')
        return redirect(url_for('main.submit'))
    
@user_bp.route('/my-submissions')
@login_required
def my_submissions():
    print("Is authenticated:", current_user.is_authenticated)
    print("Current user:", current_user)
    submissions = PriceEntry.query.filter_by(submitted_by=current_user.user_id).all()
    return render_template('user/mysubmission.html', submissions=submissions)


@user_bp.route('/logout/')
@login_required
def logout():
    logout_user()
    session.pop('useronline', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('main.home_page'))


@user_bp.route('/profile/')
def profile():
    return redirect(url_for('main.dashboard'))


@user_bp.route('/get_lgas/<int:state_id>')
def get_lgas(state_id):
    lgas = LGA.query.filter_by(state_id=state_id).order_by(LGA.lga_name).all()
    data = []
    for lga in lgas:
        data.append({
            "id": lga.lga_id, "name":lga.lga_name
        })
    return jsonify(data)

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return "Access Denied: Admins only", 403
        return f(*args, **kwargs)
    return decorated

@user_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    return "Welcome Admin! Here you can manage users, products, etc."


@user_bp.route('/day-old-prices')
def day_old_prices():
    DAY_OLD_PRODUCT_IDS = [24, 25, 26, 27]

    state_id = request.args.get('state_id', type=int)
    product_id = request.args.get('product_id', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    show_all = request.args.get('show_all')

    base_query = PriceEntry.query.filter(
        PriceEntry.product_id.in_(DAY_OLD_PRODUCT_IDS),
        PriceEntry.is_approved == True
    )

    if state_id:
        base_query = base_query.filter(PriceEntry.state_id == state_id)
    if product_id:
        base_query = base_query.filter(PriceEntry.product_id == product_id)
    if from_date:
        base_query = base_query.filter(PriceEntry.date_submitted >= from_date)
    if to_date:
        base_query = base_query.filter(PriceEntry.date_submitted <= to_date + ' 23:59:59')

    if show_all == '1' or from_date or to_date:
        prices = base_query.order_by(PriceEntry.date_submitted.desc()).all()
    else:
        subq = base_query.with_entities(
            PriceEntry.product_id,
            PriceEntry.hatchery_id,
            func.max(PriceEntry.date_submitted).label('max_date')
        ).group_by(PriceEntry.product_id, PriceEntry.hatchery_id).subquery()

        prices = PriceEntry.query.join(
            subq,
            (PriceEntry.product_id == subq.c.product_id) &
            (PriceEntry.hatchery_id == subq.c.hatchery_id) &
            (PriceEntry.date_submitted == subq.c.max_date)
        ).order_by(PriceEntry.date_submitted.desc()).all()

    day_old_products = Product.query.filter(Product.product_id.in_(DAY_OLD_PRODUCT_IDS)).all()
    states = State.query.all()

    return render_template(
        'user/day_old_prices.html',
        prices=prices,
        day_old_products=day_old_products,
        states=states,
        selected_state=state_id,
        selected_product=product_id,
        from_date=from_date,
        to_date=to_date,
        show_all=show_all
    )