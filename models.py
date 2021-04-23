from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

from datetime import datetime

bcrypt = Bcrypt()
db = SQLAlchemy()



class Follows(db.Model):
    """Connection of user following which group."""

    __tablename__ = 'follows'

    group_being_followed_id = db.Column(
        db.Integer,
        db.ForeignKey('groups.id', ondelete="cascade"),
        primary_key=True, 
        
    )

    user_following_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True, 
        
    )


class User(db.Model):
    """Create a site user."""

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        unique=True,
        primary_key=True,
        autoincrement=True
        
    )

    username = db.Column(
        db.String(20),
        nullable=False,
        unique=True,
        
    )
    password = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    bio = db.Column(db.Text)

    groups = db.relationship("Group")

    post = db.relationship("Post")

    favorite = db.relationship("Favorite")

    following = db.relationship(
        "Group",
        secondary="follows",
        primaryjoin=(Follows.user_following_id == id)
    )
    
  

    
    # start of convenience class methods

    def is_following(self, other_group):
        """Is this user following a group?"""

        found_group_list = [group for group in self.following if group == other_group]
        return len(found_group_list) == 1
        

    @classmethod
    def register(cls, username, password, first_name, last_name, email):
        """Register a user, hashing their password."""

        hashed = bcrypt.generate_password_hash(password)
        hashed_utf8 = hashed.decode("utf8")
        user = cls(
            username=username,
            password=hashed_utf8,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Validate that user exists & password is correct.

        Return user if valid; else return False.
        """

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            return user
        else:
            return False


class Group(db.Model):
    """All diet groups"""

    __tablename__ = 'groups'

    id = db.Column(
        db.Integer,
        primary_key=True,
        unique = True, 
        autoincrement=True
         
    )

    title = db.Column(
        db.String(140),
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=False,
    )

    creator_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    followers = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.group_being_followed_id == id)
    )
    

    user = db.relationship('User')
    post = db.relationship("Post")

 
    
    @classmethod
    def register(cls, title, creator_id, description):
        """Register a user, hashing their password."""

        hashed = bcrypt.generate_password_hash(password)
        hashed_utf8 = hashed.decode("utf8")
        group = cls(
            title=title,
            creator_id=creator_id,
            description=description
        )

        db.session.add(group)
        return group
    


class Post(db.Model):
    """All diet groups"""

    __tablename__ = 'posts'

    id = db.Column(
        db.Integer,
        primary_key=True,
        unique= True, 
        autoincrement=True
        
    )

    title = db.Column(
        db.String(300),
        nullable=False,
    )

    text = db.Column(
        db.String(1000),
        nullable=False,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow(),
    )

    group_id = db.Column(
        db.Integer, 
        db.ForeignKey('groups.id', ondelete='CASCADE'),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )

    #ids = db.relationship("Group", secondary="users")

    user = db.relationship('User')
    group = db.relationship('Group')

class Favorite(db.Model):
    """Favorites meals"""

    __tablename__ = 'favorites' 

    id = db.Column(
        db.Integer,
        primary_key=True, 
        unique=True, 
        autoincrement=True
        
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade')
    )

    img = db.Column(
        db.Text
    )

    meal_id = db.Column(db.Integer, nullable=False)

    user = db.relationship("User")

def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)