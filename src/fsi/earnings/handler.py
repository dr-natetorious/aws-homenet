from rttnewsclient import RttNewsEarningsClient
from json import dumps

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
calendar = RttNewsEarningsClient()

@app.route('/heartbeat')
def hello_world():
  return 'Hello, World!'

@app.route('/<date_str>')
def fetch_by_date(date_str):
  return dumps([x.to_hash() for x in calendar.get_for_date(date_str=date_str)])
  