from datetime import datetime, date
from flask_login import UserMixin

from pkg import db


class State(db.Model):
    __tablename__ = 'states'
    state_id = db.Column(db.Integer, primary_key=True)
    state_name = db.Column(db.String(100), nullable=False)

class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))

class LGA(db.Model):
    __tablename__ = 'lgas'
    lga_id = db.Column(db.Integer, primary_key=True)
    lga_name = db.Column(db.String(100), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('states.state_id'), nullable=False)

    state = db.relationship('State', backref='lgas')
    price_entries = db.relationship('PriceEntry', back_populates='lga')
    markets = db.relationship('Market', back_populates='lga')

    def __repr__(self):
        return f'<LGA {self.lga_name}>'


class Market(db.Model):
    __tablename__ = 'markets'
    market_id = db.Column(db.Integer, primary_key=True)
    market_name = db.Column(db.String(100), nullable=False)
    lga_id = db.Column(db.Integer, db.ForeignKey('lgas.lga_id'), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('states.state_id'), nullable=False)

    lga = db.relationship('LGA', back_populates='markets')
    state = db.relationship('State', backref='markets')
    price_entries = db.relationship('PriceEntry', back_populates='market')


class PriceEntry(db.Model):
    __tablename__ = 'price_entries'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('states.state_id'), nullable=False)
    lga_id = db.Column(db.Integer, db.ForeignKey('lgas.lga_id'), nullable=False)
    market_id = db.Column(db.Integer, db.ForeignKey('markets.market_id'), nullable=True)
    hatchery_id = db.Column(db.Integer, db.ForeignKey('hatcheries.hatchery_id'), nullable=True)
    source_type = db.Column(db.Enum('Farm', 'Market', name='source_type'), nullable=True)
    notes = db.Column(db.String(255))
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)

    # Relationships - these are what make the HTML work
    product = db.relationship('Product', backref='price_entries')
    user = db.relationship('User', backref='price_entries', foreign_keys=[submitted_by])
    market = db.relationship('Market', back_populates='price_entries')
    state = db.relationship('State', backref='price_entries')
    lga = db.relationship('LGA', back_populates='price_entries')
    hatchery = db.relationship('Hatchery', backref='price_entries')

    def __repr__(self):
        return f"<PriceEntry {self.id} product={self.product_id} price={self.price}>"
    

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True) # match ERD
    product_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    product_image = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=True)
    unit_of_measure = db.Column(db.String(20), server_default='Kg')    


    category = db.relationship('Category', backref='products')

    @property
    def name(self):
        return self.product_name  


class Hatchery(db.Model):
    __tablename__ = 'hatcheries'
    hatchery_id = db.Column(db.Integer, primary_key=True)
    hatchery_name = db.Column(db.String(100), unique=True, nullable=False)
    contact = db.Column(db.String(100))
    is_active = db.Column(db.Integer, default=1)
    distribution_days = db.Column(db.String(100), nullable=True)
    

class DayOldPrice(db.Model):
    __tablename__ = 'day_old_prices' # add this too
    day_old_id = db.Column(db.Integer, primary_key=True)
    hatchery_id = db.Column(db.Integer, db.ForeignKey('hatcheries.hatchery_id'), nullable=False)
    bird_type = db.Column(db.Enum('Broiler', 'Cockerel', 'Layer', 'Turkey'), nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    availability = db.Column(db.Enum('Available', 'Sold Out', 'Pre-order'), default='Available')
    state_id = db.Column(db.Integer, db.ForeignKey('states.state_id'), nullable=False)
    price_date = db.Column(db.Date, nullable=False)
    day_of_week = db.Column(db.Enum('Monday', 'Thursday'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved'), default='approved')
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    # relationships to make queries easy
    hatchery = db.relationship('Hatchery', backref='day_old_prices') 
    state = db.relationship('State', backref='day_old_prices')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(45), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20))
    state_id = db.Column(db.Integer, db.ForeignKey('states.state_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    def get_id(self):
        return str(self.user_id)    
