#!/usr/local/bin/python3
import rtsp
import boto3
import io
from time import sleep
from datetime import datetime
from os import environ
from signal import signal, SIGTERM
from PIL import Image

def get_setting(name) ->str:
  value = environ.get(name)
  if value is None:
    raise ValueError('MissingValue: '+name)
  return value

server_uri = get_setting('SERVER_URI') #'rtsp://admin:EYE_SEE_YOU@192.168.0.70/live2'#get_setting('RTSP_URI')
region = 'us-east-1' #get_setting('AWS_REGION')
sensor=get_setting('CAMERA')
bucket= get_setting('BUCKET') #'nbachmei.personal.video.us-east-1'

s3 = boto3.client('s3', region_name=region)

def process_image(image:Image):
  if image is None:
    print('No frame.')
    return
  
  array = io.BytesIO()
  image.save(array, format='PNG')

  key = '{}/{}.png'.format(sensor,datetime.now().strftime('%H%M.%S.%f'))
  try:
    s3.put_object(
      Bucket=bucket,
      Key=key,
      Body=array.getvalue(),
      Metadata={
        'Sensor':sensor,
        'Year': str(datetime.now().year),
        'Month': str(datetime.now().month),
      })

    print('Wrote Frame {}: {}'.format(key, image))
  except Exception as error:
    print('Unable to write frame: '+error)

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def run_continously():
  while(True):
    main_loop()

def main_loop():  
  with rtsp.Client(rtsp_server_uri=server_uri) as client:
    if not client.isOpened():
      print('rtsp server is not running.')
      # sleep(15)
      return

    image = client.read()
    while True:
      try:
        process_image(image)
        image = client.read()
      except Exception as e:
        print(e)

def handler(request, context):
  with rtsp.Client(rtsp_server_uri=server_uri) as client:
    if not client.isOpened():
      print('rtsp server is not running.')
      return {
        'Error': 'rtsp server is offline'
      }

    image = client.read()
    while True:
      try:
        process_image(image)
        image = client.read()
      except Exception as e:
        print(e)
        return {
          'Error': 'rtsp server disconnected'+str(e)
        }

  return { 'Status': 'OK'}

if __name__ == '__main__':
  signal(SIGTERM, shutdown)
  run_continously()
  #return