# -*- coding: utf-8 -*-
import os
from random import choice
from PIL import Image
from flask import Flask, render_template, redirect, url_for,  session, request, g
from flask_wtf import FlaskForm
from flask_login import LoginManager, UserMixin, login_required, login_user
from flask_login import logout_user, current_user
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import TextAreaField, FileField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import EmailField
from data import db_session
from data.users import User
from data.works import Work
from data.photos import Photo
from data.voites import Voite


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired()])
    about = TextAreaField("Немного о себе")
    submit = SubmitField('Войти')


class AddWorkForm(FlaskForm):
    title = StringField('Наименование работы', validators=[DataRequired()])
    description = TextAreaField("Описание работы")
    registered_only = BooleanField("Показывать только зарегистрированным пользователям")
    submit = SubmitField('Отправить')


class DeleteForm(FlaskForm):
    submit = SubmitField('Да')


class UploadForm(FlaskForm):
    alt = StringField('Alt-подпись')
    title = StringField('Заголовок')
    file = FileField(validators=[DataRequired()])
    submit = SubmitField('Отправить')


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"
    

def generate_filename(old):
    filename = ""
    for i in range(30):
        filename += choice("1234567890_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    filename += "." + old.split(".")[-1]
    return filename


@login_manager.user_loader
def user_loader(user_id):
    session = db_session.create_session()
    return session.query(User).filter(User.id == user_id).first()


@app.before_request
def before_request():
    g.user = current_user


@app.route('/')
@app.route('/index')
def index():
    session = db_session.create_session()
    works = session.query(Work).all()
    for work in works:
        photo = session.query(Photo).filter(Photo.work_id == work.id).first()
        if photo:
            work.photo_name = photo.filename
        else:
            work.photo_name = None
        work.voites_count =  session.query(Voite).filter(Voite.work_id == work.id).count()
        if (g.user.is_authenticated and
            (work.user_id == g.user.id or 
             session.query(Voite).filter((Voite.work_id == work.id) &
                                         (Voite.user_id == g.user.id)).count() != 0)):
            work.voite = False
        else:
            work.voite = True
    return render_template('index.html', title='Выставка мастеров', works=works, voite=g.user.is_authenticated)


@app.route('/work/<work_id>', methods=['GET', 'POST'])
def work_index(work_id):
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    if work:
        user = session.query(User).filter(User.id == work.user_id).first()
        photos =  session.query(Photo).filter(Photo.work_id == work.id)
        if (g.user.is_authenticated and
                (work.user_id == g.user.id or 
                 session.query(Voite).filter((Voite.work_id == work.id) &
                                             (Voite.user_id == g.user.id)).count() != 0)):
            voite = False
        else:
            voite = True        
        return render_template('work1.html', title='Работа: ' + work.title,
                               work=work, user=user, photos=photos, voite=voite)
    else:
        return render_template('work1.html', title='Работа не найдена')


@app.route('/voite/<work_id>', methods=['GET', 'POST'])
@login_required
def voite(work_id):
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    if work:
        if work and work.user_id == g.user.id:
            result = "Нельзя голосовать за свои работы"
        elif session.query(Voite).filter((Voite.work_id == work_id) & (Voite.user_id == g.user.id)).count() != 0:
            result = "Вы уже голосовали за эту работу"
        else:
            voite = Voite(user_id=g.user.id, work_id=work_id)
            session.add(voite)
            session.commit()
            result = "Спасибо за ваш голос"
    else:
        result = "Работа не найдена"
    return render_template('voite.html', title=result)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.name == form.username.data).first()
#        user = User.query.filter_by(name=form.username.data).first()
        if user is None:
            error = 'Неверное имя пользователя или пароль'
            return render_template('login.html', title='Авторизация', error=error, form=form)
        is_correct_password = user.check_password(form.password.data)
        print(is_correct_password)
        if not is_correct_password:
            error = 'Неверное имя пользователя или пароль'
            return render_template('login.html', title='Авторизация', error=error,
                                   form=form)
        login_user(user)
        return redirect('/user')
    return render_template('login.html', title='Авторизация', form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/user')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/user')
@login_required
def user():
    session = db_session.create_session()
    works = session.query(Work).filter(Work.user_id == g.user.id)
    return render_template('user.html', title='Страница пользователя ' + g.user.name,
                           works=works)


@app.route('/user/add_work', methods=['GET', 'POST'])
@login_required
def add_work():
    form = AddWorkForm()
    if form.validate_on_submit():
        work = Work(
            title=form.title.data,
            description=form.description.data,
            registered_only=form.registered_only.data,
            user_id=g.user.id)
        session = db_session.create_session()
        session.add(work)
        session.commit()
        return redirect('/user')
    return render_template('add_work.html', title='Добавление новой работы', form=form)


@app.route('/user/edit_work/<work_id>', methods=['GET', 'POST'])
@login_required
def edit_work(work_id):
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    # проверяем, существует ли работа и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        form = AddWorkForm(obj=work)
        if request.method == 'POST' and form.validate_on_submit():
            work.title = form.title.data
            work.description=form.description.data
            work.registered_only=form.registered_only.data
            session.commit()
            return redirect('/user/work/' + str(work_id))
        return render_template('edit_work.html', title='Редактирование информации о работе', form=form)
    else:
        return render_template('edit_work.html', title='Работа не найдена')


@app.route('/user/delete_work/<work_id>', methods=['GET', 'POST'])
@login_required
def delete_work(work_id):
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    # проверяем, существует ли работа и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        form = DeleteForm()
        if request.method == 'POST' and form.validate_on_submit():
            # удаляем записи о фотографиях и фотографии с сервера
            photos = session.query(Photo).filter(Photo.work_id == work_id)
            for photo in photos:
                if os.path.exists("static/photos/" + photo.filename):
                    os.remove("static/photos/" + photo.filename)                
                if os.path.exists("static/photos/tumb_" + photo.filename):
                    os.remove("static/photos/tumb_" + photo.filename)                
            session.query(Photo).filter(Photo.work_id == work_id).delete()
            # удаляем записи о голосах за работу
            session.query(Voite).filter(Voite.work_id == work_id).delete()
            # удаляем запись о работе
            session.delete(work)
            session.commit()
            return redirect('/user')
        return render_template('delete_work.html', title='Удаление работы', form=form, work=work)
    else:
        return render_template('delete_work.html', title='Работа не найдена')


@app.route('/user/upload_photo/<work_id>', methods=['GET', 'POST'])
@login_required
def upload_file(work_id):
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    # проверяем, существует ли работа и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        form = UploadForm()
        if form.validate_on_submit():
            filename = generate_filename(form.file.data.filename)
            form.file.data.save('static/photos/' + filename)
            # сохраняем информацию о файле в БД
            photo = Photo(
                work_id=work_id,
                title=form.title.data,
                alt=form.alt.data,
                filename=filename)
            session = db_session.create_session()
            session.add(photo)
            session.commit()
            # обрезаем загруженное изображение до квадратного
            img = Image.open('static/photos/' + filename)
            size = min(img.size)
            img1 = img.crop( (0,0,size,size) )
            img1.save('static/photos/' + filename)
            # создаем иконку
            img2 = img1.resize((200, 200))
            img2.save('static/photos/tumb_' + filename)
            return redirect('/user/work/' + str(work_id))
        return render_template('upload_photo.html', form=form, work=work)        
    else:
        return render_template('upload_photo.html', title='Работа не найдена')


@app.route('/user/delete_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def delete_photo(photo_id):
    session = db_session.create_session()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        work = session.query(Work).filter(Work.id == photo.work_id).first()
    # проверяем, существует ли фотография и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        form = DeleteForm()
        if request.method == 'POST' and form.validate_on_submit():
            # удаляем фотографию
            if os.path.exists("static/photos/" + photo.filename):
                os.remove("static/photos/" + photo.filename)                
            if os.path.exists("static/photos/tumb_" + photo.filename):
                os.remove("static/photos/tumb_" + photo.filename)                
            session.delete(photo)
            session.commit()
            return redirect('/user/work/' + str(work.id))
        return render_template('delete_photo.html', title='Удаление фотографии', form=form, photo=photo)
    else:
        return render_template('delete_photo.html', title='Фотография не найдена')


@app.route('/user/mirrorv_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def mirrorv_photo(photo_id):
    session = db_session.create_session()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        work = session.query(Work).filter(Work.id == photo.work_id).first()
    # проверяем, существует ли фотография и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        # поворачиваем изображение
        img = Image.open('static/photos/' + photo.filename)
        img1 = img.transpose(Image.FLIP_LEFT_RIGHT)
        filename = generate_filename(photo.filename)
        img1.save('static/photos/' + filename)
        # создаем иконку
        img2 = img1.resize((200, 200))
        img2.save('static/photos/tumb_' + filename)
        if os.path.exists("static/photos/" + photo.filename):
            os.remove("static/photos/" + photo.filename)                
        if os.path.exists("static/photos/tumb_" + photo.filename):
            os.remove("static/photos/tumb_" + photo.filename)                
        photo.filename = filename
        session.commit()
        return redirect('/user/work/' + str(work.id))
    else:
        return redirect('/user')


@app.route('/user/mirrorh_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def mirrorh_photo(photo_id):
    session = db_session.create_session()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        work = session.query(Work).filter(Work.id == photo.work_id).first()
    # проверяем, существует ли фотография и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        # поворачиваем изображение
        img = Image.open('static/photos/' + photo.filename)
        img1 = img.transpose(Image.FLIP_TOP_BOTTOM)
        filename = generate_filename(photo.filename)
        img1.save('static/photos/' + filename)
        # создаем иконку
        img2 = img1.resize((200, 200))
        img2.save('static/photos/tumb_' + filename)
        if os.path.exists("static/photos/" + photo.filename):
            os.remove("static/photos/" + photo.filename)                
        if os.path.exists("static/photos/tumb_" + photo.filename):
            os.remove("static/photos/tumb_" + photo.filename)                
        photo.filename = filename
        session.commit()
        return redirect('/user/work/' + str(work.id))
    else:
        return redirect('/user')


@app.route('/user/rotateccv_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def rotateccv_photo(photo_id):
    session = db_session.create_session()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        work = session.query(Work).filter(Work.id == photo.work_id).first()
    # проверяем, существует ли фотография и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        # поворачиваем изображение
        img = Image.open('static/photos/' + photo.filename)
        img1 = img.transpose(Image.ROTATE_90)
        filename = generate_filename(photo.filename)
        img1.save('static/photos/' + filename)
        # создаем иконку
        img2 = img1.resize((200, 200))
        img2.save('static/photos/tumb_' + filename)
        if os.path.exists("static/photos/" + photo.filename):
            os.remove("static/photos/" + photo.filename)                
        if os.path.exists("static/photos/tumb_" + photo.filename):
            os.remove("static/photos/tumb_" + photo.filename)                
        photo.filename = filename
        session.commit()
        return redirect('/user/work/' + str(work.id))
    else:
        return redirect('/user')


@app.route('/user/rotatecv_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def rotatecv_photo(photo_id):
    session = db_session.create_session()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        work = session.query(Work).filter(Work.id == photo.work_id).first()
    # проверяем, существует ли фотография и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        # поворачиваем изображение
        img = Image.open('static/photos/' + photo.filename)
        img1 = img.transpose(Image.ROTATE_270)
        filename = generate_filename(photo.filename)
        img1.save('static/photos/' + filename)
        # создаем иконку
        img2 = img1.resize((200, 200))
        img2.save('static/photos/tumb_' + filename)
        if os.path.exists("static/photos/" + photo.filename):
            os.remove("static/photos/" + photo.filename)                
        if os.path.exists("static/photos/tumb_" + photo.filename):
            os.remove("static/photos/tumb_" + photo.filename)                
        photo.filename = filename
        session.commit()
        return redirect('/user/work/' + str(work.id))
    else:
        return redirect('/user')


@app.route('/user/rotate180_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def rotate180_photo(photo_id):
    session = db_session.create_session()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        work = session.query(Work).filter(Work.id == photo.work_id).first()
    # проверяем, существует ли фотография и принадлежит ли она пользователю
    if work and work.user_id == g.user.id:
        # поворачиваем изображение
        img = Image.open('static/photos/' + photo.filename)
        img1 = img.transpose(Image.ROTATE_180)
        filename = generate_filename(photo.filename)
        img1.save('static/photos/' + filename)
        # создаем иконку
        img2 = img1.resize((200, 200))
        img2.save('static/photos/tumb_' + filename)
        if os.path.exists("static/photos/" + photo.filename):
            os.remove("static/photos/" + photo.filename)                
        if os.path.exists("static/photos/tumb_" + photo.filename):
            os.remove("static/photos/tumb_" + photo.filename)                
        photo.filename = filename
        session.commit()
        return redirect('/user/work/' + str(work.id))
    else:
        return redirect('/user')


@app.route('/user/work/<work_id>', methods=['GET', 'POST'])
@login_required
def work(work_id):
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    if work and work.user_id == g.user.id:
        photos =  session.query(Photo).filter(Photo.work_id == work.id)
        return render_template('work.html', title='Работа: ' + work.title,
                               work=work, photos=photos)
    else:
        return render_template('work.html', title='Работа не найдена')


@app.route('/admin')
@login_required
def admin():
    if g.user.id != 1:
        return redirect('/')
    session = db_session.create_session()
    works = session.query(Work).all()
    return render_template('admin.html', title='Страница администратора ' + g.user.name,
                           works=works)


@app.route('/admin/edit_work/<work_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_work(work_id):
    if g.user.id != 1:
        return redirect('/')
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    # проверяем, существует ли работа
    if work:
        form = AddWorkForm(obj=work)
        if request.method == 'POST' and form.validate_on_submit():
            work.title = form.title.data
            work.description=form.description.data
            work.registered_only=form.registered_only.data
            session.commit()
            return redirect('/admin/work/' + str(work_id))
        return render_template('edit_work.html', title='Редактирование информации о работе', form=form)
    else:
        return render_template('edit_work.html', title='Работа не найдена')


@app.route('/admin/delete_work/<work_id>', methods=['GET', 'POST'])
@login_required
def admin_delete_work(work_id):
    if g.user.id != 1:
        return redirect('/')
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    # проверяем, существует ли работа
    if work:
        # удаляем записи о фотографиях и фотографии с сервера
        photos = session.query(Photo).filter(Photo.work_id == work_id)
        for photo in photos:
            if os.path.exists("static/photos/" + photo.filename):
                os.remove("static/photos/" + photo.filename)                
            if os.path.exists("static/photos/tumb_" + photo.filename):
                os.remove("static/photos/tumb_" + photo.filename)                
        session.query(Photo).filter(Photo.work_id == work_id).delete()
        # удаляем записи о голосах за работу
        session.query(Voite).filter(Voite.work_id == work_id).delete()
        # удаляем запись о работе
        session.delete(work)
        session.commit()
        return redirect('/admin')
    else:
        return render_template('delete_work.html', title='Работа не найдена')


@app.route('/admin/delete_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def admin_delete_photo(photo_id):
    if g.user.id != 1:
        return redirect('/')
    session = db_session.create_session()
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    # проверяем, существует ли фотография
    if photo:
        work = session.query(Work).filter(Work.id == photo.work_id).first()
        # удаляем фотографию
        if os.path.exists("static/photos/" + photo.filename):
            os.remove("static/photos/" + photo.filename)                
        if os.path.exists("static/photos/tumb_" + photo.filename):
            os.remove("static/photos/tumb_" + photo.filename)                
        session.delete(photo)
        session.commit()
        return redirect('/admin/work/' + str(work.id))
    else:
        return render_template('delete_photo.html', title='Фотография не найдена')


@app.route('/admin/work/<work_id>', methods=['GET', 'POST'])
@login_required
def admin_work(work_id):
    if g.user.id != 1:
        return redirect('/')
    session = db_session.create_session()
    work = session.query(Work).filter(Work.id == work_id).first()
    if work:
        photos =  session.query(Photo).filter(Photo.work_id == work.id)
        return render_template('work_admin.html', title='Работа: ' + work.title,
                               work=work, photos=photos)
    else:
        return render_template('work_admin.html', title='Работа не найдена')


@app.route('/admin/users')
@login_required
def admin_users():
    if g.user.id != 1:
        return redirect('/')
    session = db_session.create_session()
    users = session.query(User).all()
    return render_template('admin_users.html', title='Список пользователей', users=users)


@app.route('/admin/delete_user/<user_id>', methods=['GET', 'POST'])
@login_required
def admin_delete_user(user_id):
    if g.user.id != 1:
        return redirect('/')
    session = db_session.create_session()
    user = session.query(User).filter(User.id == user_id).first()
    # проверяем, существует ли пользователь
    if user:
        # получаем список работ пользователя
        works = session.query(Work).filter(Work.user_id == user_id)
        for work in works:
            # удаляем записи о фотографиях и фотографии с сервера
            photos = session.query(Photo).filter(Photo.work_id == work.id)
            for photo in photos:
                if os.path.exists("static/photos/" + photo.filename):
                    os.remove("static/photos/" + photo.filename)                
                if os.path.exists("static/photos/tumb_" + photo.filename):
                    os.remove("static/photos/tumb_" + photo.filename)                
            session.query(Photo).filter(Photo.work_id == work.id).delete()
            # удаляем записи о голосах за работу
            session.query(Voite).filter(Voite.work_id == work.id).delete()
            # удаляем запись о работе
            session.delete(work)
        # удаляем пользователя
        session.delete(user)
        session.commit()
        return redirect('/admin/users')
    else:
        return redirect('/admin/users')


if __name__ == '__main__':
    db_session.global_init("db/blogs.sqlite")
    app.run(port=8080, host='127.0.0.1')