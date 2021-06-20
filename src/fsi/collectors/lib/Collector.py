#!/usr/bin/env python3
from typing import List, Mapping
import ratelimitqueue
from td.client import ExdLmtError
from td.exceptions import GeneralError
from lib.ClientFactory import ClientFactory
from os import environ
from json import dumps
from logging import getLogger
from time import sleep
from ratelimitqueue import RateLimitQueue
import boto3
from os import environ
from base64 import b64encode
from uuid import uuid1

logger = getLogger()
factory = ClientFactory()
tdclient = factory.create_client()
max_calls = 60 # maximum is 120
kinesis = boto3.client('kinesis')
stream_name = environ.get('STREAM_NAME')

def fetch_all_instruments(assetTypes:list)->Mapping[str,List[str]]:
  """
  Enumerates through all symbols
  """
  symbols = {}
  filter_count=0
  queue = RateLimitQueue(calls=30, per=1)
  for alpha in list(range(65,91)) + list(range(48,57)):
    prefix = '.*'+chr(alpha)
    queue.put(prefix)

  while(queue.qsize() > 0):  
    try:
      prefix = queue.get()
      instruments = tdclient.search_instruments(
        symbol=prefix,
        projection='symbol-regex')
    except ExdLmtError as error:
      print('Error (sleep 10sec): '+str(error))
      queue.put(prefix)
      sleep(10)
      continue
    except GeneralError:
      # Response too big, split into subcalls...
      print('Response too big; splitting...')
      suffix = prefix[-1].replace('.*','')
      for ch in list(range(65,91)) + list(range(48,57)):
        prefix = '.*{}{}'.format(chr(ch),suffix)
        queue.put(prefix)
      continue
    except Exception as error:
      print('Error:'+str(error))
      continue

    print('Query Prefix {} found {} instruments...'.format(
      prefix, len(instruments)))

    for symbol in instruments.keys():
      assetType = instruments[symbol]['assetType']
      if not assetType in assetTypes:
        filter_count+=1
        continue
      
      if not assetType in symbols:
        symbols[assetType] = [symbol]
      else:
        symbols[assetType].append(symbol)      

  print('Returning {} instruments with {} filtered...'.format(
    len(symbols), filter_count)
  )
  
  return symbols
    
def fetch_fundamental_data(symbols:list):
  """
  Fetches list of instruments fundamental data
  """
  queue = RateLimitQueue(calls=max_calls)
  [queue.put(x) for x in symbols]

  while queue.qsize() > 0:
    symbol = queue.get()
    
    # Submit the fundamental data
    response = tdclient.search_instruments(
      symbol=symbol,
      projection='fundamental')

    # Attempt to unpack the payload
    try:      
      content = response[symbol]['fundamental']
    except KeyError:
      continue

    send_service_data(
      serviceName='FUNDAMENTAL',
      contents=[content])

def fetch_quotes_data(symbols:list):
  """
  Fetches list of instruments fundamental data
  """
  queue = RateLimitQueue(calls=max_calls)
  [queue.put(x) for x in list(chunks(symbols,100)) ]

  while queue.qsize() > 0:
    instruments = queue.get()
    print('Processing batch {}'.format(instruments))
    
    # Submit the fundamental data
    response = tdclient.get_quotes(
      instruments=instruments)
    
    # Attempt to unpack the payload
    try:
      contents = list(response.values())
    except KeyError:
      print('KeyError for batch - {}'.format(instruments))
      continue
    except AttributeError:
      print('AttributeError for batch - {}'.format(instruments))
      continue

    send_service_data(
      serviceName='QUOTE',
      contents=contents)

def send_service_data(serviceName:str, contents:list) -> None:
  if serviceName is None:
    raise ValueError('No serviceName provided')
  if len(contents) == 0:
    logger.warn('empty list given to send_service_data')
    return

  message = dumps({
    'data':[
      {
        'service':serviceName,
        'content':contents
      }
    ]
  })

  # TODO: Is this causing double wrapping in GraphBuilder
  data = b64encode(bytes(message,'utf-8'))

  print('Sending[{}]: {} base64 bytes'.format(stream_name,len(data)))
  response = kinesis.put_record(
    StreamName= stream_name,
    Data=data,
    PartitionKey= str(uuid1())
  )

  print('Response: {}'.format(dumps(response)))

def chunks(lst, n):
  """Yield successive n-sized chunks from lst."""
  for i in range(0, len(lst), n):
    yield lst[i:i + n]