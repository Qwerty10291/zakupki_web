import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm

class User(SqlAlchemyBase):
    __tablename__ = 'user'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    role = sqlalchemy.Column(sqlalchemy.String, default='user')
    is_approved = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    is_banned = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    is_parsing = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    reg_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())
    auth = orm.relation('Auth', back_populates="user")
    history = orm.relation('History', back_populates='user')

class Auth(SqlAlchemyBase):
    __tablename__ = 'Auth'
    
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'))
    login = sqlalchemy.Column(sqlalchemy.String)
    password = sqlalchemy.Column(sqlalchemy.String)
    email = sqlalchemy.Column(sqlalchemy.String)
    user = orm.relation('User')

class History(SqlAlchemyBase):
    __tablename__ = 'history'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'))
    state = sqlalchemy.Column(sqlalchemy.String)
    tag = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    min_price = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    max_price = sqlalchemy.Column(sqlalchemy.BigInteger, default=999999999)
    date_from = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    date_to = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())
    sort_filter = sqlalchemy.Column(sqlalchemy.String, default="Дате+размещения")
    sort_direction = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    document = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())
    user = orm.relation('User')

class Applications(SqlAlchemyBase):
    __tablename__ = 'applications'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'))
    date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())
    user = orm.relation('User')

class Data(SqlAlchemyBase):
    __tablename__ = 'data'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    type = sqlalchemy.Column(sqlalchemy.String)
    tender_price = sqlalchemy.Column(sqlalchemy.Float)
    tender_date = sqlalchemy.Column(sqlalchemy.DateTime)
    tender_object = sqlalchemy.Column(sqlalchemy.String)
    customer = sqlalchemy.Column(sqlalchemy.String)
    tender_adress = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    tender_delivery = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    tender_terms = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    tender_object_info = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    document_links = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    tender_link = sqlalchemy.Column(sqlalchemy.String)
    winner = orm.relation('Winners', back_populates='data')


class Winners(SqlAlchemyBase):
    __tablename__ = 'winner'

    data_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('data.id'), primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    position = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    price = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    data = orm.relation('Data')

    def __hash__(self) -> int:
        return hash(self.name)