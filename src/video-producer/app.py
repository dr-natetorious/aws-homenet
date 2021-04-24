#!/usr/local/bin/python3
#!/usr/local/bin/python3
import rtsp
import boto3
import io
from time import sleep
from datetime import datetime
from signal import signal, SIGTERM
from PIL import Image
from processor import Producer
from configuration import Configuration

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def handler(request, context):
  config = Configuration.from_request(request)
  producer = Producer(config)
  producer.invoke()

def run_continously():
  config = Configuration.from_environment()
  while(True):
    try:
      Producer(config).invoke()
    except Exception as error:
      print(error)

if __name__ == '__main__':
  signal(SIGTERM, shutdown)
  run_continously()
  #return
