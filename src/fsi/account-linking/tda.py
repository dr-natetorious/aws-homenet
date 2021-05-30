import urllib
import time
from json import dumps
from datetime import datetime
from os import environ
from logging import getLogger
import requests

logger = getLogger(__name__)

class AccountLinkingClient:
  """
  Represents a client for linking Ameritrade 
  """
  def __init__(self, client_id:str=None, redirect_uri:str=None) -> None:
    # Default the values if not provided.
    if client_id is None:    
      client_id = environ.get('TDA_CLIENT_ID')
    if redirect_uri is None:
      redirect_uri = environ.get('TDA_REDIRECT_URI')

    if client_id is None:
      raise AssertionError('client_id is not available') 

    if redirect_uri is None:
      raise AssertionError('redirect_uri is not available')

    self.client_id=client_id
    self.redirect_uri=redirect_uri

  def create_credentials_from_urlcode(self, url_code:str) -> dict:
    """
    Creates the contents for a td_state.json credential document.
    """
    if url_code is None:
      raise AssertionError('url_code is not available')

    # Define the parameters of our access token post.
    data = {
      'grant_type': 'authorization_code',
      'client_id': self.client_id + '@AMER.OAUTHAP',
      'access_type': 'offline',
      'code': url_code,
      'redirect_uri': self.redirect_uri
    }

    print({
      'url':'https://api.tdameritrade.com/v1/oauth2/token',
      'headers':{'Content-Type':'application/x-www-form-urlencoded'}, 
      'data':data
    })

    response = requests.post(
      url='https://api.tdameritrade.com/v1/oauth2/token',
      headers={'Content-Type':'application/x-www-form-urlencoded'}, 
      data=data)

    if response is None:
      raise AssertionError('Unable to translate the code to token')

    token_dict = response.json()
    print('Response = {}'.format(token_dict))

    # Compute the additional expected values
    if 'refresh_token_expires_in' not in token_dict:
      token_dict['refresh_token_expires_in'] = token_dict['expires_in']

    access_token_expire = time.time() + int(token_dict['expires_in'])
    refresh_token_expire = time.time() + int(token_dict['refresh_token_expires_in'])
    token_dict['access_token_expires_at'] = access_token_expire
    token_dict['refresh_token_expires_at'] = refresh_token_expire
    token_dict['logged_in'] = True
    token_dict['access_token_expires_at_date'] = datetime.utcfromtimestamp(access_token_expire).isoformat()
    token_dict['refresh_token_expires_at_date'] = datetime.utcfromtimestamp(refresh_token_expire).isoformat()
    
    return token_dict
