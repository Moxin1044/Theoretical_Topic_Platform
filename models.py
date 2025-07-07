from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum

db = SQLAlchemy()

# Association table for many-to-many relationship between papers and questions
paper_questions = db.Table('paper_questions',
    db.Column('paper_id', db.Integer, db.ForeignKey('paper.id'), primary_key=True),
    db.Column('question_id', db.Integer, db.ForeignKey('question.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(Enum('single_choice', 'multiple_choice', 'essay', 'fill_blank', name='question_types'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON)  # For choice questions
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', backref=db.backref('questions', lazy=True))
    papers = db.relationship('Paper', secondary=paper_questions, back_populates='questions')

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'content': self.content,
            'options': self.options,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Paper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', backref=db.backref('papers', lazy=True))
    questions = db.relationship('Question', secondary=paper_questions, back_populates='papers')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'question_count': len(self.questions),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 