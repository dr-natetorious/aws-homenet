from enum import Enum
import logging
from datetime import datetime
from math import fabs
from typing import Any, List, Mapping
from ratelimitqueue.ratelimitqueue import RateLimitGetMixin
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError, NotFndError
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
from lib.StateStore import StateStore

class RunStatus(Enum):
  MORE_AVAILABLE='MORE_AVAILABLE'
  COMPLETE='COMPLETE'

class Collector:
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    assert tdclient != None, "No tdclient"
    assert state_store != None, "No state store"

    self.__tdclient= tdclient
    self.__state_store = state_store

  @property
  def tdclient(self)->TDClient:
    return self.__tdclient

  @property
  def state_store(self)->TDClient:
    return self.__state_store

  def run(self)->RunStatus:
    raise NotImplementedError()

  def ignore_instrument(self,instrument)->bool:
    if not 'symbol' in instrument:
      return True

    return Collector.is_garbage_symbol(instrument['symbol'])

  def create_symbol_queue_from_marker(self)->RateLimitQueue:
     # Check if the progress marker exists...
    progress = self.state_store.get_progress(self.__class__.__name__)
    if progress != None and "marker" in progress:
      marker = progress['marker']
    else:
      marker = ''

     # Populate the unfinished tasks list...
    queue = RateLimitQueue(calls=100, per=60, fuzz=0.5)
    ignored = []
    filtered = []
    for instrument in self.state_store.retrieve_equities():
      # Check this is valid record
      symbol = StateStore.default_value(instrument,'symbol',default=None)
      if symbol == None:
        continue
      
      # Check if the derived class wants to ignore
      if self.ignore_instrument(instrument):
        ignored.append(symbol)
        continue
      
      # Check if the progress marker wants to skip
      if symbol < marker:
        filtered.append(symbol)
        continue
      
      # All checks pass add into the job list
      queue.put(instrument)
    
    if len(ignored)>0:
      print('CreateQueue: Ignoring: {}'.format(len(ignored)))
    if len(filtered)>0:
      print('CreateQueue: Filtered: {}'.format(len(filtered)))
    return queue

  @staticmethod
  def is_garbage_symbol(symbol:str)->bool:
    for ch in symbol:
      if ch.isdigit():
        return True
      elif ch == '-':
        return True
      elif ch == ' ':
        return True
    return False

  @staticmethod
  def attempt_with_retry(action, retry_count:int=3)->Any:
    """
    Perform an action and automatically retry failures.
    """
    attempts = 0
    while attempts < retry_count:
      try:
        return action()
      except ExdLmtError as throttled:
        print('Throttled Detected - Sleep additional 5 seconds')
        sleep(5)
      except NotFndError:
        print('Resource not found')
        return None
      except Exception as error:
        print(str(error))
        attempts += 1

      sleep(attempts * attempts)

    # Validate the response is valid
    raise GeneralError(
      'Unable to {} within {} attempts.'.format(action, retry_count))

class QueuedCollector(Collector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  def process_instrument(self,instrument:dict)->Any:
    raise NotImplementedError()

  def persist_batch(self,batch:List[Any])->None:
    raise NotImplementedError()

  @property
  def batch_size(self)->int:
    return 25

  #@xray_recorder.capture('OptionableDiscovery::run')
  def run(self, max_items:int=99999)->RunStatus:
    """
    Discovers which symbols are optionable.
    """
    queue = self.create_symbol_queue_from_marker()
    if queue.unfinished_tasks == 0:
      raise ValueError('No tasks discovered; this is likely a defect.')

    # Process the queue until empty...
    responses = []
    completed = 0
    skipped = 0
    total = queue.unfinished_tasks
    while queue.qsize() >0:
      try:
        # Perform the instrument assessment...
        instrument = queue.get()
        assessment = self.process_instrument(instrument)
        completed += 1

        if assessment != None:
          responses.append(assessment)
        else:
          skipped += 1
        
        # Periodically checkpoint and display progress
        if len(responses) >0 and len(responses) % self.batch_size == 0:
          self.persist_batch(responses)
          self.state_store.set_progress(self.__class__.__name__, responses[-1]['symbol'])
          responses.clear()
          print('[{}] Completed {} / {} [{}%].  Skipped {}.'.format(
            datetime.now(), 
            completed, 
            total, 
            round(completed/total*100,2),
            skipped))

        # Check if we reached the run limit
        if completed >= max_items:
          return RunStatus.MORE_AVAILABLE
      except ExdLmtError as error:
        print('Error (sleep 5): '+str(error))
        sleep(5)
        queue.put(instrument)
        continue

    # Publish any remaining items in the buffer
    if len(responses) > 0:
      self.persist_batch(responses)
    self.state_store.clear_progress(self.__class__.__name__)
    return RunStatus.COMPLETE
