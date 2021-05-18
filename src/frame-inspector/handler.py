import boto3
import urllib
from os import environ
from json import dumps
from botocore.retries import bucket
from flask import request, redirect
from rekclient import RekClient

client = RekClient(region_name='us-east-1')
bucket_name = environ.get('BUCKET_NAME')
if bucket_name is None:
  bucket_name= 'nbachmei.personal.video.v2.us-east-1'

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

@app.route('/inspect/<path:key>')
def inspect(key:str):
  labels = client.detect_s3_labels(
    app.logger,
    's3://{}/{}'.format(bucket_name, key))

  return labels.as_dict()

if __name__ == '__main__':
  app.run(debug=True)
