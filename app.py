from flask import Flask, render_template, redirect, url_for, flash, request, abort, Response, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Book, Genre, Cover, Review, ViewHistory
from forms import LoginForm, BookForm, ReviewForm, DateRangeForm
import os
import hashlib
import markdown
from bleach import clean
from datetime import datetime, timedelta
from sqlalchemy.sql import func
import csv
from io import StringIO
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/covers'

# --- Init ---
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Кастомный фильтр для преобразования Markdown в HTML
@app.template_filter('markdown_to_html')
def markdown_to_html(text):
    return markdown.markdown(text, extensions=['fenced_code', 'tables'])

# --- Главная с пагинацией ---
@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    per_page = 10
    books = Book.query.order_by(Book.year.desc()).paginate(page=page, per_page=per_page)

    # Популярные книги (за последние 3 месяца)
    three_months_ago = datetime.utcnow() - timedelta(days=90)
    popular_books = (
        db.session.query(Book, func.count(ViewHistory.id).label('view_count'))
        .join(ViewHistory)
        .filter(ViewHistory.timestamp >= three_months_ago)
        .group_by(Book.id)
        .order_by(func.count(ViewHistory.id).desc())
        .limit(5)
        .all()
    )
    popular_books = [book for book, view_count in popular_books]

    # Недавно просмотренные книги
    session_id = request.cookies.get('session_id', str(uuid.uuid4()))
    recent_books = (
        db.session.query(Book)
        .join(ViewHistory)
        .filter(ViewHistory.session_id == session_id)
        .order_by(ViewHistory.timestamp.desc())
        .limit(5)
        .all()
    )

    resp = make_response(render_template('index.html', books=books, popular_books=popular_books, recent_books=recent_books))
    if not request.cookies.get('session_id'):
        resp.set_cookie('session_id', session_id, max_age=31536000)  # 1 year
    return resp

# --- Просмотр книги ---
@app.route('/book/<int:book_id>')
def view_book(book_id):
    book = Book.query.get_or_404(book_id)
    reviews = Review.query.filter_by(book_id=book_id).order_by(Review.timestamp.desc()).all()

    # Регистрация просмотра
    session_id = request.cookies.get('session_id', str(uuid.uuid4()))
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    view_count = ViewHistory.query.filter(
        ViewHistory.book_id == book_id,
        ViewHistory.session_id == session_id,
        ViewHistory.timestamp >= today_start
    ).count()
    if view_count < 10:
        view = ViewHistory(
            book_id=book_id,
            user_id=current_user.id if current_user.is_authenticated else None,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(view)
        db.session.commit()

    user_review = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(book_id=book_id, user_id=current_user.id).first()

    resp = make_response(render_template('view_book.html', book=book, reviews=reviews, user_review=user_review))
    if not request.cookies.get('session_id'):
        resp.set_cookie('session_id', session_id, max_age=31536000)  # 1 year
    return resp

# --- Добавление рецензии ---
@app.route('/review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()

    # Проверка: не оставлял ли пользователь уже рецензию на эту книгу
    existing_review = Review.query.filter_by(book_id=book_id, user_id=current_user.id).first()
    if existing_review:
        flash('Вы уже оставили рецензию на эту книгу.', 'warning')
        return redirect(url_for('view_book', book_id=book_id))

    if form.validate_on_submit():
        try:
            review = Review(
                text=clean(form.text.data),
                rating=form.rating.data,
                user_id=current_user.id,
                book_id=book_id,
                timestamp=datetime.utcnow()
            )
            db.session.add(review)
            db.session.commit()
            flash('Рецензия добавлена!', 'success')
            return redirect(url_for('view_book', book_id=book_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении рецензии: {str(e)}', 'danger')
    else:
        if request.method == 'POST':
            errors = form.errors
            flash(f'При сохранении рецензии возникла ошибка: {errors}', 'danger')

    return render_template('review_form.html', form=form, book=book)

# --- Добавление книги ---
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
        return redirect(url_for('index'))

    form = BookForm()
    form.genres.choices = [(g.id, g.name) for g in Genre.query.all()]

    if form.validate_on_submit():
        try:
            book = Book(
                title=form.title.data,
                description=clean(form.description.data),  # Санитизация Markdown
                year=form.year.data,
                publisher=form.publisher.data,
                author=form.author.data,
                pages=form.pages.data
            )
            selected_genres = Genre.query.filter(Genre.id.in_(form.genres.data)).all()
            book.genres = selected_genres
            db.session.add(book)
            db.session.flush()  # Получаем book.id без коммита

            if form.cover.data:
                file = form.cover.data
                content = file.read()
                md5 = hashlib.md5(content).hexdigest()
                existing_cover = Cover.query.filter_by(md5_hash=md5).first()
                if existing_cover:
                    book.cover = existing_cover
                else:
                    filename = f"{book.id}_{secure_filename(file.filename)}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    new_cover = Cover(filename=filename, mimetype=file.mimetype, md5_hash=md5, book=book)
                    db.session.add(new_cover)

            db.session.commit()
            flash('Книга успешно добавлена!', 'success')
            return redirect(url_for('view_book', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
    else:
        if request.method == 'POST':
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')

    return render_template('book_form.html', form=form, show_cover_field=True)

# --- Редактирование книги ---
@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if current_user.role.name not in ['Администратор', 'Модератор']:
        flash('У вас недостаточно прав.', 'danger')
        return redirect(url_for('index'))

    form = BookForm(obj=book)
    form.genres.choices = [(g.id, g.name) for g in Genre.query.all()]

    if request.method == 'GET':
        form.genres.data = [g.id for g in book.genres]

    if form.validate_on_submit():
        try:
            book.title = form.title.data
            book.description = clean(form.description.data)  # Санитизация Markdown
            book.year = form.year.data
            book.publisher = form.publisher.data
            book.author = form.author.data
            book.pages = form.pages.data
            book.genres = Genre.query.filter(Genre.id.in_(form.genres.data)).all()
            db.session.commit()
            flash('Книга обновлена', 'success')
            return redirect(url_for('view_book', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')

    return render_template('book_form.html', form=form, title='Редактировать книгу', show_cover_field=False)

# --- Удаление книги ---
@app.route('/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
        return redirect(url_for('index'))
    book = Book.query.get_or_404(book_id)
    if book.cover:
        cover_path = os.path.join(app.config['UPLOAD_FOLDER'], book.cover.filename)
        if os.path.exists(cover_path):
            os.remove(cover_path)
    db.session.delete(book)
    db.session.commit()
    flash('Книга удалена', 'success')
    return redirect(url_for('index'))

# --- Статистика ---
@app.route('/statistics', methods=['GET'])
@login_required
def statistics():
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
        return redirect(url_for('index'))

    tab = request.args.get('tab', 'logs')
    page = request.args.get('page', 1, type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    form = DateRangeForm(date_from=date_from, date_to=date_to)

    if tab == 'logs':
        query = ViewHistory.query.order_by(ViewHistory.timestamp.desc())
        if date_from:
            query = query.filter(ViewHistory.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(ViewHistory.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        view_logs = query.paginate(page=page, per_page=10)
        return render_template('statistics.html', active_tab='logs', view_logs=view_logs, form=form)
    else:
        query = db.session.query(Book.title, func.count(ViewHistory.id).label('view_count'))\
            .join(ViewHistory, Book.id == ViewHistory.book_id)\
            .filter(ViewHistory.user_id != None)\
            .group_by(Book.id)\
            .order_by(func.count(ViewHistory.id).desc())
        if date_from:
            query = query.filter(ViewHistory.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(ViewHistory.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        view_stats = query.paginate(page=page, per_page=10)
        return render_template('statistics.html', active_tab='stats', view_stats=view_stats, form=form)

# --- Экспорт журнала в CSV ---
@app.route('/export_logs_csv')
@login_required
def export_logs_csv():
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
        return redirect(url_for('index'))

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    query = ViewHistory.query.order_by(ViewHistory.timestamp.desc())
    if date_from:
        query = query.filter(ViewHistory.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(ViewHistory.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    view_logs = query.all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['№', 'Пользователь', 'Книга', 'Дата и время'])
    for i, view in enumerate(view_logs, 1):
        user_name = view.user.full_name() if view.user else 'Неаутентифицированный пользователь'
        cw.writerow([i, user_name, view.book.title, view.timestamp.strftime('%Y-%m-%d %H:%M')])

    output = si.getvalue()
    si.close()
    filename = f'view_logs_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )

# --- Экспорт статистики в CSV ---
@app.route('/export_stats_csv')
@login_required
def export_stats_csv():
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
        return redirect(url_for('index'))

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    query = db.session.query(Book.title, func.count(ViewHistory.id).label('view_count'))\
        .join(ViewHistory, Book.id == ViewHistory.book_id)\
        .filter(ViewHistory.user_id != None)\
        .group_by(Book.id)\
        .order_by(func.count(ViewHistory.id).desc())
    if date_from:
        query = query.filter(ViewHistory.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(ViewHistory.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    view_stats = query.all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['№', 'Книга', 'Количество просмотров'])
    for i, (title, view_count) in enumerate(view_stats, 1):
        cw.writerow([i, title, view_count])

    output = si.getvalue()
    si.close()
    filename = f'view_stats_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )

# --- Вход ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Успешный вход', 'success')
            return redirect(url_for('index'))
        flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')
    return render_template('login.html', form=form)

# --- Выход ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists('library.db'):
        with app.app_context():
            db.create_all()
            print('✅ База данных создана')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=False, host='0.0.0.0')