from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import math
# For file uploading
import os
from werkzeug.utils import secure_filename
#importing json module to connect to json file
import json
from flask_mail import Mail


with open('config.json', 'r') as c:
    params = json.load(c)["params"]


local_server = True
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']
# For mail
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail_uname'],
    MAIL_PASSWORD = params['gmail_pw']
)
mail = Mail(app)
# Connecting to database
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']
db = SQLAlchemy(app)


# This class defines tables of database
class Contacts(db.Model):
    '''
    sno, name, email, ph_num, msg, date
    '''
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    ph_num = db.Column(db.String(120), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)

    def __init__(self, name, ph_num, msg, email, date):
        self.name = name
        self.ph_num = ph_num
        self.msg = msg
        self.date = date
        self.email = email


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    tagline = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(20), nullable=True)

    def __init__(self, title, slug, content, date, tagline, img_file):
        self.title = title
        self.slug = slug
        self.content = content
        self.date = date
        self.tagline = tagline
        self.img_file = img_file


@app.route("/")
def home():
    # Pagination Logic
    # Searching for some posts from database
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    #[:params['no_of_posts']]  # Allow only 5 latest posts
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page - 1)*int(params['no_of_posts']): (page - 1)*int(params['no_of_posts']) + int(params['no_of_posts'])]
    # First
    if page == 1:
        prev = "#"
        next = "/?page=" + str(page+1)
    # Last
    elif page == last:
        prev = "/?page=" + str(page-1)
        next = "#"
    # Middle
    else:
        prev = "/?page=" + str(page-1)
        next = "/?page=" + str(page+1)

    # Searching for some posts from database
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)  # Rendering a particular page


@app.route("/about")  # To a different page
def about():
    return render_template('about.html', params=params)


@app.route("/dashboard", methods=['GET', 'POST'])  # To a different page
def login():
    # For POST requests
    # If already logged in
    if 'user' in session and session['user'] == params['admin_uname']:
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)
        return render_template('dashboard.html', params=params)
    if request.method=='POST':
        # Redirect to admin panel
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if (username == params['admin_uname']) and (userpass == params['admin_pw']):
            # Set the session variable
            session['user'] = username
            # Fetch all posts for the table
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts = posts)
    else:
        return render_template('login.html', params=params)


@app.route("/contact", methods=['GET', 'POST'])  # Adding GET and POST
def contact():
    if (request.method=='POST'):
        '''Add entry to database'''
        name = request.form.get('name')
        email = request.form.get('email')
        ph_num = request.form.get('ph_num')
        msg = request.form.get('msg')
        '''LHS: Column in table, RHS: Values from above'''
        entry = Contacts(name=name, ph_num=ph_num, email=email, msg=msg, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        '''Send message from user'''
        mail.send_message('New message from ' + name + ' via CodeSnap!',
                          sender=email,
                          recipients=[params['gmail_uname']],
                          body=msg + "\n" + ph_num
                        )
    return render_template('contact.html', params=params)


@app.route("/post/<string:post_slug>", methods=['GET'])  # To a different page
def post_route(post_slug):
    # Fetching post from database
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if 'user' in session and session['user'] == params['admin_uname']:
        if request.method == 'POST':
            # Fetching from the form
            title = request.form.get('title')
            tagline = request.form.get('tagline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if sno == '0':
                # Adding a new post
                post = Posts(title=title, tagline=tagline, slug=slug, content=content, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
            else:
                # Editing an existing post
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.slug = slug
                post.tagline = tagline
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post)


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if 'user' in session and session['user'] == params['admin_uname']:
        if request.method == 'POST':
            # Upload a file
            f = request.files['file1']
            # Save file
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded successfully"


@app.route("/logout")
def logout():
    # Killing the session variable
    session.pop('user')
    return redirect('/dashboard')


@app.route("/delete/<string:sno>")
def delete(sno):
    if 'user' in session and session['user'] == params['admin_uname']:
        post = Posts.query.filter_by(sno=sno).first()
        # Delete a post
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


app.run(debug=True)  # Start the server, debug=True helps in changing within live server


# Static folder: Public
# Template folder: Private
