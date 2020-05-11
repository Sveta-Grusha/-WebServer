import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Voite(UserMixin, SqlAlchemyBase):
    __tablename__ = 'voites'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    work_id = sqlalchemy.Column(sqlalchemy.Integer, 
                                   sqlalchemy.ForeignKey("works.id"))
    user_id = sqlalchemy.Column(sqlalchemy.Integer, 
                                   sqlalchemy.ForeignKey("users.id"))
    work = orm.relation('Work')
    user = orm.relation('User')
