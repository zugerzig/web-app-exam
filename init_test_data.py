from models import db, User, Role, Book, Genre
from werkzeug.security import generate_password_hash
from app import app
from random import sample

with app.app_context():
    db.create_all()

    # Добавление ролей
    admin_role = Role.query.filter_by(name='Администратор').first()
    if not admin_role:
        admin_role = Role(name='Администратор', description='Полный доступ')
        db.session.add(admin_role)

    moder_role = Role.query.filter_by(name='Модератор').first()
    if not moder_role:
        moder_role = Role(name='Модератор', description='Редактирование книг и рецензий')
        db.session.add(moder_role)

    user_role = Role.query.filter_by(name='Пользователь').first()
    if not user_role:
        user_role = Role(name='Пользователь', description='Может оставлять рецензии')
        db.session.add(user_role)

    db.session.commit()

    # Добавление пользователей
    users = [
        {'username': 'admin', 'password': 'adminpass', 'last_name': 'Админов', 'first_name': 'Админ', 'middle_name': 'Админович', 'role': admin_role},
        {'username': 'mod', 'password': 'modpass', 'last_name': 'Модеров', 'first_name': 'Мод', 'middle_name': 'Модович', 'role': moder_role},
        {'username': 'user', 'password': 'userpass', 'last_name': 'Юзеров', 'first_name': 'Юзер', 'middle_name': 'Юзерович', 'role': user_role}
    ]
    for user_data in users:
        if not User.query.filter_by(username=user_data['username']).first():
            user = User(
                username=user_data['username'],
                password_hash=generate_password_hash(user_data['password']),
                last_name=user_data['last_name'],
                first_name=user_data['first_name'],
                middle_name=user_data['middle_name'],
                role=user_data['role']
            )
            db.session.add(user)
    db.session.commit()

    # Добавление жанров
    genre_names = ['Фантастика', 'Приключения', 'Научные', 'Детектив', 'Фэнтези', 'Роман']
    genres = []
    for name in genre_names:
        genre = Genre.query.filter_by(name=name).first()
        if not genre:
            genre = Genre(name=name)
            db.session.add(genre)
        genres.append(genre)
    db.session.commit()

    # Добавление книг
    books_data = [
        {'title': 'Звёздный путь', 'description': 'Про космос и приключения.', 'year': 2020, 'publisher': 'КосмоИздат', 'author': 'Иван Космонавтов', 'pages': 320, 'genres': ['Фантастика', 'Приключения']},
        {'title': 'Мозг и разум', 'description': 'Научные исследования о мозге.', 'year': 2021, 'publisher': 'НаукаПресс', 'author': 'Доктор Разумов', 'pages': 280, 'genres': ['Научные']},
        {'title': 'Тайна старого замка', 'description': 'Детективная история в средневековом замке.', 'year': 2019, 'publisher': 'МистикаБук', 'author': 'Анна Загадкина', 'pages': 350, 'genres': ['Детектив']},
        {'title': 'Путешествие к звёздам', 'description': 'Эпическое путешествие через галактику.', 'year': 2022, 'publisher': 'КосмоИздат', 'author': 'Сергей Звездолётов', 'pages': 400, 'genres': ['Фантастика', 'Приключения']},
        {'title': 'Меч и магия', 'description': 'Фэнтезийная сага о героях и драконах.', 'year': 2020, 'publisher': 'ФэнтезиПресс', 'author': 'Елена Чародейка', 'pages': 450, 'genres': ['Фэнтези']},
        {'title': 'Любовь на закате', 'description': 'Романтическая история двух сердец.', 'year': 2023, 'publisher': 'Романтика', 'author': 'Мария Сердцева', 'pages': 300, 'genres': ['Роман']},
        {'title': 'Код вселенной', 'description': 'Научное исследование космоса.', 'year': 2021, 'publisher': 'НаукаПресс', 'author': 'Алексей Учёнов', 'pages': 320, 'genres': ['Научные']},
        {'title': 'Секреты сыщика', 'description': 'Приключения частного детектива.', 'year': 2018, 'publisher': 'ДетективКлуб', 'author': 'Игорь Следов', 'pages': 280, 'genres': ['Детектив']},
        {'title': 'Легенды древнего леса', 'description': 'Фэнтезийные истории о лесных духах.', 'year': 2022, 'publisher': 'ФэнтезиПресс', 'author': 'Ольга Лесная', 'pages': 360, 'genres': ['Фэнтези']},
        {'title': 'Город теней', 'description': 'Детектив в мрачном мегаполисе.', 'year': 2020, 'publisher': 'МистикаБук', 'author': 'Дмитрий Тёмный', 'pages': 340, 'genres': ['Детектив']},
        {'title': 'Космический странник', 'description': 'Одиссея одинокого космонавта.', 'year': 2023, 'publisher': 'КосмоИздат', 'author': 'Пётр Галактов', 'pages': 380, 'genres': ['Фантастика']},
        {'title': 'Сердце дракона', 'description': 'Эпическая фэнтези-сага.', 'year': 2019, 'publisher': 'ФэнтезиПресс', 'author': 'Александр Огненный', 'pages': 420, 'genres': ['Фэнтези']},
        {'title': 'Наука будущего', 'description': 'Прогнозы развития технологий.', 'year': 2024, 'publisher': 'НаукаПресс', 'author': 'Виктор Технов', 'pages': 310, 'genres': ['Научные']},
        {'title': 'Песни ветра', 'description': 'Романтическая история на фоне природы.', 'year': 2022, 'publisher': 'Романтика', 'author': 'Екатерина Ветрова', 'pages': 290, 'genres': ['Роман']},
        {'title': 'Загадка пропавшего корабля', 'description': 'Морские приключения и тайны.', 'year': 2021, 'publisher': 'МореКниг', 'author': 'Николай Моряков', 'pages': 330, 'genres': ['Приключения']},
        {'title': 'Тёмная звезда', 'description': 'Фантастический триллер.', 'year': 2020, 'publisher': 'КосмоИздат', 'author': 'Михаил Чернов', 'pages': 370, 'genres': ['Фантастика']},
        {'title': 'Убийство в полночь', 'description': 'Классический детектив.', 'year': 2017, 'publisher': 'ДетективКлуб', 'author': 'Светлана Ночная', 'pages': 300, 'genres': ['Детектив']},
        {'title': 'Волшебный лес', 'description': 'Сказка для всех возрастов.', 'year': 2023, 'publisher': 'ФэнтезиПресс', 'author': 'Ирина Сказкина', 'pages': 280, 'genres': ['Фэнтези']},
        {'title': 'Искры гениальности', 'description': 'Биографии великих учёных.', 'year': 2022, 'publisher': 'НаукаПресс', 'author': 'Геннадий Умов', 'pages': 350, 'genres': ['Научные']},
        {'title': 'Путь воина', 'description': 'Приключения в древнем мире.', 'year': 2019, 'publisher': 'МореКниг', 'author': 'Роман Героев', 'pages': 340, 'genres': ['Приключения']},
        {'title': 'Свет далёких звёзд', 'description': 'Фантастическая сага о космосе.', 'year': 2024, 'publisher': 'КосмоИздат', 'author': 'Юлия Звёздная', 'pages': 390, 'genres': ['Фантастика', 'Приключения']}
    ]

    for book_data in books_data:
        if not Book.query.filter_by(title=book_data['title']).first():
            book = Book(
                title=book_data['title'],
                description=book_data['description'],
                year=book_data['year'],
                publisher=book_data['publisher'],
                author=book_data['author'],
                pages=book_data['pages']
            )
            book_genres = [genre for genre in genres if genre.name in book_data['genres']]
            book.genres = book_genres
            db.session.add(book)

    db.session.commit()
    print(f'✅ Добавлено {Book.query.count()} книг, {User.query.count()} пользователей, {Role.query.count()} ролей, {Genre.query.count()} жанров.')