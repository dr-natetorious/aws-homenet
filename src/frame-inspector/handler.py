import boto3
import urllib
from os import environ
from json import dumps
from flask import request, redirect

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

# @app.route('/')
# def login():
#   data = {
#     'response_type':'code',
#     'redirect_uri':linkingClient.redirect_uri,
#     'client_id':linkingClient.client_id + '@AMER.OAUTHAP'
#   }
#   params = urllib.parse.urlencode(data)
#   url = 'https://auth.tdameritrade.com/auth?' +params

#   return redirect(url)

# @app.route('/connect')
# def connect():
#   code = request.args.get('code')
#   tda_creds = linkingClient.create_credentials_from_urlcode(code)

#   response = secrets.update_secret(
#     SecretId=secret_id,
#     SecretString=dumps(tda_creds)
#   )

#   return dumps(response)
