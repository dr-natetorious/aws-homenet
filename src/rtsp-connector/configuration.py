from os import environ

class Configuration:
  def __init__(self, server_uri=None, camera_name=None, bucket_name=None):
    self.server_uri = server_uri
    self.camera_name = camera_name
    self.bucket_name = bucket_name

  def __str__(self):
    return "Config:[{} -> {}]".format(
      self.camera_name,
      self.bucket_name)

  @property
  def camera_name(self)->str:
    return self.__camera_name

  @camera_name.setter
  def camera_name(self, value)->None:
    self.__camera_name = value

  @property
  def server_uri(self)->str:
    return self.__server_uri

  @server_uri.setter
  def server_uri(self, value)->None:
    self.__server_uri = value

  @property
  def bucket_name(self)->str:
    return self.__bucket

  @bucket_name.setter
  def bucket_name(self, value)->None:
    self.__bucket = value

  @staticmethod
  def __get_setting(name) ->str:
    value = environ.get(name)
    if value is None:
      raise ValueError('MissingValue: '+name)
    return value

  @staticmethod
  def from_environment():
    print('from_environment')
    
    result = Configuration()
    result.server_uri = "rtsp://{}".format(Configuration.__get_setting('SERVER_URI'))
    result.bucket = Configuration.__get_setting('BUCKET')
    return result

  @staticmethod
  def from_request(request:dict):
    result = Configuration()
    result.server_uri = request['SERVER_URI']
    result.bucket_name = request['BUCKET']
    return result
