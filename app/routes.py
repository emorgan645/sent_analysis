from datetime import datetime

import joblib
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from pandas import read_csv
from werkzeug.urls import url_parse

from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, EmptyForm, PostForm, InputForm
from app.get_tweets import get_tweets_classification, get_user_classification, api_key, api_secret_key, access_token_secret, access_token
from app.models import User, Post, Search, User_results

import sqlite3

database = r"C:\Users\emorg\webapp\app.db"

model_NB = joblib.load("twttr_sntmnt.pkl")

def requestResults(name, limit):
    
    user_id = current_user.id
    tweets = get_tweets_classification(user_id, name, limit)
    print(tweets)
    data = str(tweets['classification'].value_counts()) + '\n\n'

    return data + str(tweets)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])

@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {}.'.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/input', methods=['POST', 'GET'])
@login_required
def input():
    form = InputForm()
    if form.validate_on_submit():
        user_search = Search(user_id=current_user.id, keyword=form.keyword.data, limit=form.limit.data)
        db.session.add(user_search)
        db.session.commit()
        keyword = form.keyword.data
        limit = form.limit.data
        return redirect(url_for('results', name=keyword, limit=limit))
    return render_template('input.html', title='Input', form=form)


@app.route('/results/<name>/<limit>')
@login_required
def results(name, limit):

    con = sqlite3.connect(database)
    cursor = con.cursor()
    con.row_factory = sqlite3.Row

    user_id = current_user.id
    get_tweets_classification(user_id, name, limit)

    search_query = """SELECT search_id from search ORDER BY `search_id` DESC LIMIT 1"""

    cursor.execute(search_query)
    search_id = cursor.fetchall()

    resultstable = """SELECT user_results_id, search.keyword, username, created_at, tweet, place, classification
    FROM user_results
    INNER JOIN search ON user_results.search_id = search.search_id WHERE search.search_id = ?"""
    
    cursor.execute(resultstable, (int(search_id[0][0]),))
   
    rows = cursor.fetchall() 
    return render_template('results.html', title='Results', name=name, limit=limit, rows = rows)

@app.route('/user_scores')
@login_required
def scores():

    con = sqlite3.connect(database)
    cursor = con.cursor()
    con.row_factory = sqlite3.Row

    search_query = """SELECT search_id 
    FROM search 
    ORDER BY `search_id` 
    DESC LIMIT 1"""

    cursor.execute(search_query)
    search_id = cursor.fetchall()

    user_id = current_user.id
    get_user_classification(user_id, int(search_id[0][0]))

    tb_scores = """SELECT username, tb_score
    FROM twitter_details
    WHERE search_id = ?"""
    
    cursor.execute(tb_scores, (int(search_id[0][0]),))
   
    rows = cursor.fetchall() 

    return render_template('user_scores.html', title='Scores', rows=rows)

@app.route('/history')
@login_required
def history():

    con = sqlite3.connect(database)
    cursor = con.cursor()
    con.row_factory = sqlite3.Row

    userid = current_user.id

    resultstable = """SELECT user_results_id, search.keyword, username, created_at, tweet, place, classification
    FROM user_results
    INNER JOIN search ON user_results.search_id = search.search_id 
    WHERE user_results.user_id = ?"""
    
    cursor.execute(resultstable, (userid,))
   
    rows = cursor.fetchall()

    user_searches = """SELECT search_id, keyword 
    FROM search 
    WHERE search.user_id = ?"""

    cursor.execute(user_searches, (userid,))

    searches = cursor.fetchall()

    page = request.args.get('page', 1, type=int)
    tweets = Search.query.order_by(Search.keyword.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('history', page=tweets.next_num) \
        if tweets.has_next else None
    prev_url = url_for('history', page=tweets.prev_num) \
        if tweets.has_prev else None

    return render_template('history.html', title='History', rows=rows, searches=searches, posts=tweets.items,
                           next_url=next_url, prev_url=prev_url)

@app.route('/user_history')
@login_required
def user_history():

    con = sqlite3.connect(database)
    cursor = con.cursor()
    con.row_factory = sqlite3.Row

    userid = current_user.id

    user_hist = """SELECT name, username, desc, status_count, friend_count, follower_count, acc_age, tweet_avg, tb_score
    FROM twitter_details
    WHERE twitter_details.user_id = ?"""
    
    cursor.execute(user_hist, (userid,))
   
    rows = cursor.fetchall()

    user_searches = """SELECT search_id, keyword 
    FROM search 
    WHERE search.user_id = ?"""

    cursor.execute(user_searches, (userid,))

    searches = cursor.fetchall()

    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('user_history', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user_history', page=posts.prev_num) \
        if posts.has_prev else None

    return render_template('user_history.html', title='Past Users', rows=rows, searches=searches, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)
