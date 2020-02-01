import os, boto3

from flask import Flask
from config import S3_KEY, S3_SECRET


def create_app(test_config=None):
  s3 = boto3.client(
    's3',
    aws_access_key_id=S3_KEY,
    aws_secret_access_key=S3_SECRET
  )

  app = Flask(__name__, instance_relative_config=True)

  app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
  )

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

  from . import db 
  db.init_app(app)

  from . import auth
  app.register_blueprint(auth.bp)

  from . import board
  app.register_blueprint(board.bp)
  app.add_url_rule('/', endpoint='index')

  return app
