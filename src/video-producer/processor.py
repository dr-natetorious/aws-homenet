from configuration import Configuration
from rtsp import Client
from PIL import Image
from io import BytesIO
from datetime import datetime
from random import random
import boto3
import cv2

s3 = boto3.client('s3')
frame_size=(1920,1080)
sampling = 0.005

def include_sample()->bool:
  if random() < sampling:
    return True
  return False

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

      #self.capture_video(client)

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

  # def capture_video(self, client:Client)->None:
  #   print('capture_video entered')
  #   fourcc = cv2.VideoWriter_fourcc(*'avc1') #(*'mp4v')
  #   out = cv2.VideoWriter('/tmp/output.mp4',fourcc,60,frame_size)

  #   frame_count=0
  #   while True:
  #     if frame_count > 1000:
  #       print('Reached max frames')
  #       break

  #     image = client.read(raw=False)
  #     if image is None:
  #       print ('No frame, skipping')
  #       continue

  #     frame_count += 1
  #     out.write(image)
  #     print(image)

  #   out.release()
  #   self.upload_video('/tmp/output.mp4')

  def process_image(self, image:Image):
    if not include_sample():
      return
    
    if image is None:
      print('No frame to write, skipping.')
      return

    array = BytesIO()
    image.save(array, format='PNG')

    dt = datetime.now()
    key = 'eufy/{}/{}.png'.format(
      self.config.camera_name,
      dt.strftime('%Y/%m/%d/%H/%M/%S.%f'))
      
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

      print('Wrote Frame s3://{}/{}: {}'.format(self.config.bucket_name, key, image))
    except Exception as error:
      print('Unable to write frame: '+error)


  def upload_video(self, file:str):
    print('upload_video({})'.format(file))

    dt = datetime.now()
    key = 'video/{}/{}.mp4'.format(self.config.camera_name,dt.strftime('%Y/%m/%d/%H/%M.%S.%f'))
    bucket = boto3.resource('s3').Bucket(self.config.bucket_name)

    print('Uploading to s3://{}/{}'.format(
      self.config.bucket_name, key))

    bucket.upload_file(file,key)

