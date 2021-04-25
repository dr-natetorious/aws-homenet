#!/usr/local/bin/python3
from time import sleep
from signal import signal, SIGTERM
from processor import Producer
from configuration import Configuration
from json import dumps
from pythonping import ping

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def handler(request, context):
  print(dumps(request))
  config = Configuration.from_request(request)
  producer = Producer(config)
  producer.invoke()

def run_continously():
  config = Configuration.from_environment()
  while(True):
    try:
      Producer(config).invoke()
      sleep(5)
    except Exception as error:
      print(error)

if __name__ == '__main__':
  signal(SIGTERM, shutdown)
  run_continously()
  #return
