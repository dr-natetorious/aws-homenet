import boto3
import urllib
from os import environ
from json import dumps
from flask import request, redirect
from rekclient import RekClient

client = RekClient()

def init_flask_for_env():
  """
  Loads flask for lambda or local debug.
  """
  from os import environ
  if 'LOCAL_DEBUG' in environ:
    from flask import Flask
    return Flask(__name__)
  else:
    from flask_lambda import FlaskLambda
    return FlaskLambda(__name__)

app = init_flask_for_env()

@app.route('/heartbeat')
def hello_world():
  return 'Hello, World!'

@app.route('/inspect')
def inspect():
  url = request.query_string.decode()
  return url
  #json = client.detect_s3_labels(url)