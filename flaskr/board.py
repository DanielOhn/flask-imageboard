import os, boto3
from config import S3_BUCKET, S3_KEY, S3_SECRET

basedir = os.path.abspath(os.path.dirname(__file__))

from flask import (
  Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)

from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from flaskr.auth import login_required
from flaskr.db import get_db

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

bp = Blueprint('board', __name__)


## BOARDS
@bp.route('/')
def index():
  db = get_db()

  boards = db.execute(
    'SELECT b.id, link, title, body, created, author_id, username'
    ' FROM board b JOIN user u ON b.author_id = u.id'
    ' ORDER BY created DESC'
  ).fetchall()
  return render_template('board/index.html', boards=boards)


## CREATE BOARD
@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
  if request.method == 'POST':
    link = request.form['link']
    title = request.form['title']
    body = request.form['body']
    error = None

    if not title:
      error = 'title is required.'

    if error is not None:
      flash(error)
    else: 
      db = get_db()
      db.execute(
        'INSERT INTO board (link, title, body, author_id)'
        ' VALUES (?, ?, ?, ?)',
        (link, title, body, g.user['id'])
      )
      db.commit()
      return redirect(url_for('board.index'))
  return render_template('board/create.html')

## GET BOARD
## Returns a single board
def get_board(id, check_author=True):
  board = get_db().execute(
    'SELECT b.id, link, title, body, created, author_id, username'
    ' FROM board b JOIN user u ON b.author_id = u.id'
    ' WHERE b.id = ?',
    (id,)
  ).fetchone()

  if board is None:
    abort(404, "Board id {0} doesn't exist.".format(id))
  
  # if check_author and board['author_id'] != g.user['id']:
  #   abort(403)
  
  return board 

## UPDATE BOARD
@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
  board = get_board(id)

  if request.method == 'POST':
    link = request.form['link']
    title = request.form['title']
    body = request.form['body']
    error = None

    if not title:
      error = 'title is required.'
    
    if error is not None:
      flash(error)
    else:
      db = get_db()
      db.execute(
        'UPDATE board SET link = ?, title = ?, body = ?'
        ' WHERE id = ?',
        (link, title, body, id)
      )
      db.commit()
      return redirect(url_for('board.index'))
  return render_template('board/update.html', board=board)


## BOARD DELETE
@bp.route('/<int:id>/delete', methods=('POST', ))
@login_required
def delete(id):
  get_board(id)
  db = get_db()
  db.execute('DELETE FROM board WHERE id = ?', (id,))
  db.commit()
  return redirect(url_for('board.index'))

## BOARD LINK
## Returns a board by it's link/url
def get_board_link(link, check_author=True):
  board = get_db().execute(
    'SELECT b.id, link, title, body, created, author_id, username'
    ' FROM board b JOIN user u ON b.author_id = u.id'
    ' WHERE b.link = ?',
    (link,)
  ).fetchone()

  if board is None:
    abort(404, "Board id {0} doesn't exist.".format(link))
  
  if check_author and board['author_id'] != g.user['id']:
    abort(403)
  
  return board 


## BOARD DETAIL
@bp.route('/<string:link>', methods=('GET', 'POST'))
@login_required
def detail(link):
  board = get_board_link(link)

  db = get_db() 

  threads = db.execute(
    'SELECT * FROM thread t'
    ' WHERE t.board_id = {} AND t.parent_id IS NULL'.format(str(board['id']))
  ).fetchall()

  if request.method == 'POST':
    if 'file' not in request.files:
      error = 'Image is required'

    title = request.form['title']
    body = request.form['body']
    img = request.files['file']
    error = None

    if not title: 
      error = 'Title is required.'

    if img and allowed_file(img.filename):
      filename = secure_filename(img.filename)
      upload(img, filename)

    if error is not None:
      flash(error)
    else:
      db.execute(
        'INSERT INTO thread (img, title, body, author_id, board_id)'
        ' VALUES (?, ?, ?, ?, ?)',
        (filename, title, body, g.user['id'], board['id'])
      )

      db.commit()

      return redirect(url_for('board.detail', link=board['link']))
  return render_template('board/detail.html', board=board, threads=threads)

def get_thread(id):
  thread = get_db().execute(
    'SELECT * FROM thread t'
    ' WHERE t.id = ' + str(id)
  ).fetchone()

  return thread

@bp.route('/<string:link>/<int:id>', methods=('GET', 'POST'))
def thread_detail(link, id):
  board = get_board_link(link)

  db = get_db()

  threads = db.execute(
    'SELECT * FROM thread t'
    ' WHERE t.parent_id = ' + str(id)
  ).fetchall()

  if request.method == 'POST':
    images = request.files['file']
    title = request.form['title']
    body = request.form['body']
    error = None

    if not title and not body and not images:
      error = 'Please fill in one of the forms.' 

    if images and allowed_file(images.filename):
      filename = secure_filename(images.filename)
      upload(images, filename)
    else:
      filename = None

    if error is not None:
      flash(error)
    else:
      db.execute(
        'INSERT INTO thread (img, title, body, author_id, board_id, parent_id)'
        ' VALUES (?, ?, ?, ?, ?, ?)',
        (filename, title, body, g.user['id'], board['id'], id)
      )

      db.commit()

      return redirect(url_for('board.thread_detail', link=link, id=id))

  return render_template('board/thread_detail.html', board=board, threads=threads, thread=get_thread(id))

@bp.route('/<string:link>/<int:id>/delete', methods=('POST', ))
@login_required
def delete_thread(link, id):
  thread = get_thread(id)

  db = get_db()
  db.execute('DELETE FROM thread WHERE ID = ?', (id, ))
  db.commit()

  if (thread['parent_id']):
    return redirect(url_for('board.thread_detail', link=link, id=thread['parent_id']))
  
  return redirect(url_for('board.detail', link=link))

@bp.route('/<string:link>/<int:id>/edit', methods=('GET', 'POST', ))
@login_required
def update_thread(link, id):
  board = get_board_link(link)
  thread = get_thread(id)

  if request.method == 'POST':
    title = request.form['title']
    body = request.form['body']
    error = None

    if not title:
      error = 'title is required.'

    if error is not None:
      flash(error)
    else:
      db = get_db()
      db.execute(
        'UPDATE thread SET title = ?, body = ?'
        ' WHERE id = ?',
        (title, body, id)
      )
      db.commit()

      if (thread['parent_id']):
        return redirect(url_for('board.thread_detail', link=link, id=thread['parent_id']))
      else:
        return redirect(url_for('board.thread_detail', link=link, id=id))
  return render_template('board/update_thread.html', board=board, thread=thread)

def allowed_file(filename):
  return '.' in filename \
    and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload(img, filename):
  s3_resource = boto3.resource('s3')
  my_bucket = s3_resource.Bucket(S3_BUCKET)
  my_bucket.Object(filename).put(Body=img)