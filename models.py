from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# --- Связующие таблицы ---

book_genres = db.Table('book_genres',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id', ondelete='CASCADE'), primary_key=True)
)

# --- Модели ---

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    middle_name = db.Column(db.String(64), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    reviews = db.relationship('Review', backref='user', lazy=True)
    view_history = db.relationship('ViewHistory', backref='user', lazy=True)

    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name or ''}".strip()

class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    books = db.relationship('Book', secondary=book_genres, back_populates='genres')

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(128), nullable=False)
    author = db.Column(db.String(128), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    genres = db.relationship('Genre', secondary=book_genres, back_populates='books')
    cover = db.relationship('Cover', backref='book', uselist=False, cascade="all, delete")
    reviews = db.relationship('Review', backref='book', cascade="all, delete")
    view_history = db.relationship('ViewHistory', backref='book', cascade="all, delete")

    def average_rating(self):
        if not self.reviews:
            return None
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 2)

class Cover(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), nullable=False)
    mimetype = db.Column(db.String(64), nullable=False)
    md5_hash = db.Column(db.String(64), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class ViewHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    session_id = db.Column(db.String(36), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('book_id', 'user_id', 'session_id', 'timestamp', name='uix_view_limit'),
    )