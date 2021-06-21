#!/usr/bin/env python3
from math import ceil, trunc
from lib.interfaces import Collector, RunStatus
from typing import List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore
from datetime import datetime
from aws_xray_sdk.core import xray_recorder

logger = Logger('OptionableDiscovery')
batch_size = 25
class OptionableDiscovery(Collector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  @xray_recorder.capture('OptionableDiscovery::run')
  def run(self, max_items:int=99999)->RunStatus:
    """
    Discovers which symbols are optionable.
    """
    # Check if the progress marker exists...
    
    progress = self.state_store.get_progress(OptionableDiscovery.__name__)[-1]
    if progress != None and "marker" in progress:
      marker = progress['marker']
    else:
      marker = ''

    # Populate the unfinished tasks list...
    queue = RateLimitQueue(calls=100, per=60, fuzz=0.5)
    for instrument in self.state_store.retrieve_equity():
      if marker < instrument['symbol']:
        queue.put(instrument)

    # Process the queue until empty...
    responses = []
    completed = 0
    skipped = 0
    total = queue.unfinished_tasks
    while queue.qsize() >0:
      try:
        # Perform the instrument assessment...
        instrument = queue.get()
        assessment = self.check_instrument(instrument)
        completed += 1

        if assessment != None:
          responses.append(assessment)
        else:
          skipped += 1
        
        # Periodically checkpoint and display progress
        if len(responses) >0 and len(responses) % batch_size == 0:
          self.state_store.set_optionable(responses)
          self.state_store.set_progress(OptionableDiscovery.__name__, responses[-1]['symbol'])
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
      self.state_store.set_optionable(responses)
    self.state_store.clear_progress(OptionableDiscovery.__name__)
    return RunStatus.COMPLETE
  
  def check_instrument(self, instrument:dict)->bool:
    # Examine the instrument's symbol...
    symbol = instrument['symbol']
    if OptionableDiscovery.has_unlikely_symbol(symbol):
      return None

    # Query the Option Chain...
    for attempt in range(1,3):
      try:
        chain = self.tdclient.get_options_chain(
          option_chain={
            'symbol':symbol,
            'strikeCount':1})
        break
      except Exception as error:
        logger.error(str(error))
        sleep(attempt * attempt)

    if chain == None:
      return None

    # Return the query results...
    return {
      'symbol': symbol,
      'exchange': instrument['exchange'],
      'is_optionable': chain['status'] == 'SUCCESS',
      'numberOfContracts': ceil(StateStore.default_value(chain,'numberOfContracts',0)),
      'volatility': ceil(StateStore.default_value(chain,'volatility',0)),
      'isIndex': StateStore.default_value(chain,'isIndex',False),
      'isDelayed': StateStore.default_value(chain,'isDelayed',False)
    }

  @staticmethod
  def has_unlikely_symbol(symbol:str)->bool:
    for ch in symbol:
      if ch.isdigit():
        return True
      elif ch == '-':
        return True
      elif ch == ' ':
        return True
    return False
