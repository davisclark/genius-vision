from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request, url_for
#from app.exceptions import ValidationError
import simplejson as json
from . import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(64))
    api_path = db.Column(db.String(64), unique=True)
    iq = db.Column(db.Integer)
    name = db.Column(db.String(64), unique=True)
    genius_id = db.Column(db.Integer, unique=True, index=True)
    avatar_hash = db.Column(db.String(32))
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    annotations = db.relationship('Annotation', backref='author', lazy='dynamic')

    def __init__(self, title, body):
        self.artist = artist
        self.api_path = api_path
        self.iq = iq
        self.name = name
        self.genius_id = genius_id
        self.avatar_hash = avatar_hash

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    @staticmethod
    def from_json(account):
        genius_id = account.get('response.user.id')
        artist = account.get('artist')
        api_path = account.get('api_path')
        name = account.get('name')
        iq = account.get('iq')
        avatar = account.get('response.user.avatar.*size*.url')

    def __repr__(self):
        return '<User %r>' % self.name

class Song(db.Model):
    __tablename__ = 'entries'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), unique=True)
    primary_artist = db.Column(db.Text)
    pyongs_count = db.Column(db.Text)
    annotation_count = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    api_path = db.Column(db.String(120), index=True, unique=True)
    genius_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    pageviews = db.Column(db.Integer)
    annotations = db.relationship('Annotation', backref='entry', lazy='dynamic')

    def __init__(self, title, body):
        self.title = title
        self.body = body
        self.url = self.format_url(title)

    def __repr__(self):
        return '<Entry %r>' % self.title

    @staticmethod
    def format_url(title):
        url = title.replace(' ', '-').lower()
        if url.startswith('the-'):
            url = url[4:]
        url = ''.join(e for e in url if e.isalnum() or e == '-')
        return url

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'img', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'kbd']
        target.body_html = markdown(value, output_format='html')

    @staticmethod
    def from_json(json_entry):
        title = json_entry.get('title')
        if title is None or title == '':
            raise ValidationError('entry does not have a title')
        body = json_entry.get('body')
        if body is None or body == '':
            raise ValidationError('entry does not have a body')
        return Entry(title=title, body=body)


class Artist(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    genius_id = db.Column(db.String(64), index=True)
    iq = db.Column(db.Integer)
    role_for_display = db.Column(db.String(64))
    
    def __init__(self, name):
        self.name = name
        self.url = self.format_url(name)

    def __repr__(self):
        return '<Topic %r>' % self.name

    @staticmethod
    def format_url(name):
        url = name.replace(' ', '-').lower()
        if url.startswith('the-'):
            url = url[4:]
        url = ''.join(e for e in url if e.isalnum() or e == '-')
        return url


class Annotation(db.Model):
    __tablename__ = 'annotations'
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    quote = db.Column(db.Text)
    text = db.Column(db.Text)
    uri = db.Column(db.String(120))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    start = db.Column(db.String(120))
    end = db.Column(db.String(120))
    startOffset = db.Column(db.Integer)
    endOffset = db.Column(db.Integer)
    entry_id = db.Column(db.Integer, db.ForeignKey('entries.id'))

    def __init__(self, quote, text, start, end, startOffset, endOffset, *args, **kwargs):
        self.created = datetime.utcnow()
        self.quote = quote
        self.text = text
        self.start = start
        self.end = end
        self.startOffset = startOffset
        self.endOffset = endOffset


    def to_json(self):
        json_annotation = {
            "id": self.id,
            "created": str(self.created),
            "updated": str(self.updated),
            "quote": self.quote,
            "text": self.text,
            "uri": url_for('main.index', _external=True),
            "ranges": [
                {
                    "start": self.start,
                    "end": self.end,
                    "startOffset": self.startOffset,
                    "endOffset": self.endOffset
                }
            ],
            "links": [
                {
                    "href": url_for('annotate.read_annotation',
                        id=self.id,
                        _external=True),
                    "type": "text/html",
                    "rel": "alternate"
                }
            ]
        }
        return json_annotation

    @staticmethod
    def from_json(json_string):
        data = json_string
        quote = data['quote']
        if quote is None or quote == '':
            raise ValidationError('annotation does not have a quote')
        text = data['text']
        if text is None or text == '':
            raise ValidationError('annotation does not have a text')
        start = data['ranges'][0]['start']  
        if start is None or start == '':
            raise ValidationError('annotation does not have a start')
        end = data['ranges'][0]['end']
        if end is None or end == '':
            raise ValidationError('annotation does not have an end')
        startOffset = data['ranges'][0]['startOffset']
        if startOffset is None or startOffset == '':
            raise ValidationError('annotation does not have a startOffset')
        endOffset = data['ranges'][0]['endOffset']
        if endOffset is None or endOffset == '':
            raise ValidationError('annotation does not have an endOffset')
        entryUrl = data['entryUrl']
        if entryUrl is None or entryUrl == '':
            raise ValidationError('annotation does not have an entryUrl')
        return Annotation(quote=quote, text=text, start=start, end=end, startOffset=startOffset, endOffset=endOffset, entry=Entry.query.filter_by(url=entryUrl).first())


class Referent(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    entry_id = db.Column(db.Integer, db.ForeignKey('entries.id'))

    def __init__(self, body, entry, *args, **kwargs):
        self.body = body
        self.entry = entry
        self.timestamp = datetime.utcnow()
        self.author = current_user._get_current_object()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i', 'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id, _external=True),
            'post': url_for('api.get_post', id=self.post_id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)