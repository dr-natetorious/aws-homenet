from os import environ

class Configuration:
  def __init__(self, server_uri=None, camera_name=None, bucket_name=None):
    self.__server_uri = server_uri
    self.__camera_name = camera_name
    self.__bucket = bucket_name

  def __str__(self):
    return "Config:[{} -> {}]".format(
      self.camera_name,
      self.bucket_name)

  @property
  def server_uri(self)->str:
    return self.__server_uri

  @property
  def camera_name(self)->str:
    return self.__camera_name

  @property
  def bucket_name(self)->str:
    return self.__bucket

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
    result.__server_uri = Configuration.__get_setting('SERVER_URI') #'rtsp://admin:EYE_SEE_YOU@192.168.0.70/live2'#get_setting('RTSP_URI')
    result.__camera_name =Configuration.__get_setting('CAMERA')
    result.__bucket = Configuration.__get_setting('BUCKET') #'nbachmei.personal.video.us-east-1'
    return result

  @staticmethod
  def from_request(request:dict):
    result = Configuration()
    result.__server_uri = request['SERVER_URI']
    result.__camera_name = request['CAMERA']
    result.__bucket = request['BUCKET']
    return result
