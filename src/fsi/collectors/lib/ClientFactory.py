from os import environ, path, stat
from json import dumps
import boto3
from td.client import TDClient
from sys import platform, prefix
from tempfile import TemporaryDirectory
class ClientFactory:

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
  def create_client(force_refresh:bool=True) -> TDClient:
    factory = ClientFactory()
    
    outfile = TemporaryDirectory(prefix='FsiCollector')
    outpath = path.join(outfile.name,'creds.json')
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