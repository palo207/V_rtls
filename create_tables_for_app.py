from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (create_engine,
                        Column,
                        Integer,
                        String,
                        ForeignKey,
                        Table,
                        MetaData,
                        DateTime,
                        Float)
from sqlalchemy.sql import text, func 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import (server,
                    database,
                    uid, 
                    password, 
                    driver)

# Connect db
database_conn = 'mssql://{}:{}@{}/{}?driver={}'.format(uid,password,server,database,driver)
engine = create_engine(database_conn, echo = True)
Session = sessionmaker(bind=engine)

Base = declarative_base()

class users(Base):
    __tablename__ = 'users'
    id = Column(Integer,primary_key=True,autoincrement = True)
    username = Column(String(50),unique=True)
    password = Column(String(500))

class rtls_tags(Base):
    __tablename__ = 'rtls_tags'
    row_no = Column(Integer,primary_key=True,autoincrement = True)
    tag_id=Column(String(50))
    address=Column(String(50))
    PosX=Column(Float())
    PosY=Column(Float())
    zone_id=Column(String(50))
    zone_type=Column(String(50))
    zone_name=Column(String(50))
    zone_enter=Column(DateTime())
    paired=Column(Integer)
    paired_id=Column(String(50))

class logs(Base):
    __tablename__ = 'logs'
    row_no = Column(Integer,primary_key=True,autoincrement = True)
    username = Column(String(50))
    type_of_change = Column(String(50))
    tag_id=Column(String(50))
    object_id=Column(String(50))
    edit_time = Column(DateTime(timezone=True), server_default=func.now())

class tag_location(Base):
    __tablename__ = 'tag_location'
    row_no = Column(Integer,primary_key=True,autoincrement = True)
    tag_id=Column(String(50))
    x=Column(Integer)
    y=Column(Integer)

Base.metadata.create_all(bind = engine)
