#!/usr/bin/python3
import rtsp
import boto3
import io
from datetime import datetime
from os import environ

server_uri = 'rtsp://admin:EYE_SEE_YOU@192.168.0.70/live2'#get_setting('RTSP_URI')
region = 'us-east-1' #get_setting('AWS_REGION')
sensor='basemet'
bucket= 'nbachmei.personal.video.us-east-1'

s3 = boto3.client('s3', region_name=region)

def get_setting(name):
  value = environ.get(name)
  if value is None:
    raise ValueError('MissingValue: '+name)

def process_image(image):
  if image is None:
    return
  
  array = io.BytesIO()
  image.save(array, format='PNG')

  key = '{}/{}.png'.format(sensor,datetime.now.strftime('%H%M.%S.%f'))
  s3.put_object(
    Bucket=bucket,
    Key=key,
    Body=array.getvalue(),
    Metadata={
      'Sensor':sensor,
      'Year': str(datetime.now().year),
      'Month': str(datetime.now().month),
    })

  return

def process():
  with rtsp.Client(rtsp_server_uri=server_uri) as client:
    image = client.read()

    while True:
      try:
        process_image(image)
        image = client.read()
      except Exception as e:
        print(e)

if __name__ == '__main__':
  process()
  #return