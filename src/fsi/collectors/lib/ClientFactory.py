from os import environ, path
import boto3
from td.client import TDClient
from sys import platform
from aws_xray_sdk.core import xray_recorder

class ClientFactory:
  """
  Represents a factory for TDClient objects.
  """
  @property
  def td_client_id(self) -> str:
    return self.__get_value('TDA_CLIENT_ID')

  @property
  def td_redirect_uri(self)->str:
    return self.__get_value('TDA_REDIRECT_URI')
  
  @property
  def td_credentials_secret_id(self) -> str:
    return self.__get_value('TDA_SECRET_ID')

  @staticmethod
  @xray_recorder.capture('ClientFactory::create_client')
  def create_client(force_refresh:bool=True) -> TDClient:
    factory = ClientFactory()
    
    base_path = '/tmp/'
    if platform == 'win32':
      base_path = path.join(path.dirname(__file__),'..')

    #outfile = TemporaryDirectory(dir='FsiCollector')
    outpath = path.join(base_path,'creds.json')
    creds_file = factory.__fetch_credential_file(force_refresh=force_refresh, outpath=outpath)
    client = TDClient(
      client_id=factory.td_client_id,
      redirect_uri=factory.td_redirect_uri,
      credentials_path=creds_file)

    client.login()
    return client


  def __fetch_credential_file(self, outpath:str = './creds.json', force_refresh:bool=False):
    if path.exists(outpath):
      if not force_refresh:
        return outpath

    secrets = boto3.client('secretsmanager')
    response = secrets.get_secret_value(
      SecretId=self.td_credentials_secret_id)

    td_creds = response['SecretString']
    
    with open(outpath,'w') as file:
      file.write(td_creds)

    return outpath

  def __get_value(self, name):
    return environ.get(name)