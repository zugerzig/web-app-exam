from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField,
    IntegerField, SelectField, SelectMultipleField, FileField, BooleanField, DateField
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from flask_wtf.file import FileAllowed


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class BookForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    year = IntegerField('Год', validators=[DataRequired(), NumberRange(min=1000, max=2100)])
    publisher = StringField('Издательство', validators=[DataRequired(), Length(max=128)])
    author = StringField('Автор', validators=[DataRequired(), Length(max=128)])
    pages = IntegerField('Объём (стр.)', validators=[DataRequired(), NumberRange(min=1)])
    genres = SelectMultipleField('Жанры', coerce=int, validators=[DataRequired()])
    cover = FileField('Обложка', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения (.jpg, .jpeg, .png)')
    ])
    submit = SubmitField('Сохранить')


class ReviewForm(FlaskForm):
    rating = SelectField('Оценка', coerce=int, validators=[DataRequired()], choices=[
        (5, 'отлично'),
        (4, 'хорошо'),
        (3, 'удовлетворительно'),
        (2, 'неудовлетворительно'),
        (1, 'плохо'),
        (0, 'ужасно')
    ], default=5)
    text = TextAreaField('Текст рецензии', validators=[DataRequired()])
    submit = SubmitField('Сохранить')


class DateRangeForm(FlaskForm):
    date_from = DateField('Дата от', validators=[Optional()])
    date_to = DateField('Дата до', validators=[Optional()])
    submit = SubmitField('Применить')

    def validate(self):
        if not super().validate():
            return False

        if self.date_from.data and self.date_to.data:
            if self.date_from.data > self.date_to.data:
                self.date_to.errors.append('Дата "до" должна быть позже даты "от".')
                return False
        return True
