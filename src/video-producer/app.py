#!/usr/local/bin/python3
import threading
from time import sleep
from signal import signal, SIGTERM
from processor import Producer
from configuration import Configuration
from json import dumps

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def handler(request, context):
  print(dumps(request))
  config = Configuration.from_request(request)
  producer = Producer(config)
  producer.invoke()

def friendly_sleep(secs)->None:
  for _ in range(0,secs):
    sleep(1)

def run_continously(config:Configuration=None):
  if config == None:
    config = Configuration.from_environment()

  while(True):
    try:
      print('Processing: '+str(config))
      Producer(config).invoke()
      friendly_sleep(5)
    except Exception as error:
      print(error)

def run_multi_threaded():
  threads = []
  for camera_name in ['live'+str(x) for x in range(0,3)]:
    config = Configuration(
      server_uri= 'rtsp://admin:EYE_SEE_YOU@192.168.0.70/'+camera_name,
      camera_name= camera_name,
      bucket_name='nbachmei.personal.video.us-east-1')

    thread = threading.Thread(target=run_continously, args=(config,))
    threads.append(thread)
    thread.start()

  for t in threads:
    t.join()

if __name__ == '__main__':
  signal(SIGTERM, shutdown)
  #run_continously()
  run_multi_threaded()
  #return
