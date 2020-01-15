import os

from flask import Flask, send_from_directory

UPLOAD_FOLDER = os.path.join('static', 'uploads')

def create_app(test_config=None):
  app = Flask(__name__, instance_relative_config=True)

  app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
  )

  app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

  if test_config is None:
    app.config.from_pyfile('config.py', silent=True)
  else:
    app.config.from_mapping(test_config)

  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass 

  @app.route('/hello/')
  def hello():
    return 'Hello!'

  @app.route('/static/uploads/<filename>')
  def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


  from . import db 
  db.init_app(app)

  from . import auth
  app.register_blueprint(auth.bp)

  from . import board
  app.register_blueprint(board.bp)
  app.add_url_rule('/', endpoint='index')

  return app
