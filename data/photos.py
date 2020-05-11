import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Photo(UserMixin, SqlAlchemyBase):
    __tablename__ = 'photos'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    alt = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    filename = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    work_id = sqlalchemy.Column(sqlalchemy.Integer, 
                                   sqlalchemy.ForeignKey("works.id"))
    work = orm.relation('Work')