from sqlalchemy import (Column, ForeignKey, Integer, String, Boolean,
                        Table, DateTime, func)
from sqlalchemy.orm import relationship

from .database import Base

# Association table needed to create many-to-many relationship
# between items and tags
association_table = Table('item_tag', Base.metadata,
    Column('item_id', Integer, ForeignKey('item.id')),
    Column('tag_id', Integer, ForeignKey('tag.id'))
)

class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(250))
    picture_url = Column(String(250))
    tags = relationship(
        'Tag',
        # Using secondary means that entries in the association table are
        # automatically deleted when an tag is removed from an item or an
        # item is removed from a tag.
        secondary=association_table, 
        back_populates="items")

    # Columns for atom feed API
    created_on = Column(DateTime, server_default=func.now())
    updated_on = Column(DateTime,
                        server_default=func.now(),
                        onupdate=func.now())

    # Columns for dealing with authorisation
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship('User')

    def __repr__(self):
        """Method to provide pretty printing for items"""
        return "<Item: name='%s', id=%s>" % (self.name, self.id)

    def serialize(self, include_tags=False):
        """Returns object data in serializeable format"""
        result = {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'created_on': self.created_on,
            'updated_on': self.updated_on,
        }
        if include_tags:
            result['tags'] = [tag.serialize() for tag in self.tags]
        return result

class Tag(Base):
    __tablename__ = 'tag'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True)
    items = relationship(
        'Item',
        secondary=association_table,
        back_populates="tags")

    # Columns for dealing with authorisation
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship('User')

    def __repr__(self):
        """Method to provide pretty printing for tags"""
        return "<Tag: name='%s', id=%s>" % (self.name, self.id)

    def serialize(self, include_items=False):
        """Returns object data in serializeable format"""
        result = {
            'name': self.name,
            'id': self.id,
        }
        if include_items:
            result['items'] = [item.serialize() for item in self.items]
        return result


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key = True)
    name = Column(String(80), nullable = False)
    email = Column(String(80), nullable = False)
    picture = Column(String(80))
    activated = Column(Boolean, default=True)
    admin = Column(Boolean, default=False)

    def __repr__(self):
        return "<User: name='%s', email='%s', id=%s, activated=%s, admin=%s>" \
                % (self.name, self.email, self.id, self.activated, self.admin)

    @classmethod
    def getByID(cls, user_id, db_session):
        user = db_session.query(cls).filter_by(id=user_id).one()
        return user

    @classmethod
    def getIDByEmail(cls, email, db_session):
        try:
            user = db_session.query(cls).filter_by(email=email).one()
            return user.id
        except:
            return None

    @classmethod
    def createForID(cls, login_session, db_session):
        newUser = cls(name=login_session['username'],
                       email=login_session['email'],
                       picture=login_session['picture'])
        db_session.add(newUser)
        db_session.commit()
        user = db_session.query(cls).filter_by(email=login_session['email']).one()
        return user.id