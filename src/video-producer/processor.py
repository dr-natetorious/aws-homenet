from configuration import Configuration
from rtsp import Client
from PIL import Image
from io import BytesIO
from datetime import datetime
import boto3

s3 = boto3.client('s3')

class Producer:
  """
  Represents the RTSP Video Producer Component
  """  
  @property
  def config(self)->Configuration:
    return self.__config

  def __init__(self, config:Configuration)->None:
    self.__config = config

  def invoke(self)->None:
    with Client(rtsp_server_uri=self.config.server_uri) as client:
      if not client.isOpened():
        print('rtsp server is not running.')
        return {
          'Error': 'rtsp server is offline'
        }

      image = client.read()
      while True:
        try:
          self.process_image(image)
          image = client.read()
        except Exception as e:
          print(e)
          return {
            'Error': 'rtsp server disconnected'+str(e)
          }

    return { 'Status': 'OK'}

  def process_image(self, image:Image):
    if image is None:
      print('No frame, exiting early.')
      return
    
    array = BytesIO()
    image.save(array, format='PNG')

    dt = datetime.now()
    key = '{}/{}.png'.format(self.config.camera_name,dt.strftime('%Y/%m/%d/%H/%M.%S.%f'))
    try:
      s3.put_object(
        Bucket=self.config.bucket_name,
        Key=key,
        Body=array.getvalue(),
        Metadata={
          'Camera':self.config.camera_name,
          'Year': str(dt.year),
          'Month': str(dt.month),
        })

      print('Wrote Frame {}: {}'.format(key, image))
    except Exception as error:
      print('Unable to write frame: '+error)
