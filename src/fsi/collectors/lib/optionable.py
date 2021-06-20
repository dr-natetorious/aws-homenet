#!/usr/bin/env python3
from math import ceil, trunc
from td.option_chain import OptionChain
from lib.interfaces import Collector
from typing import List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore
from datetime import datetime

logger = Logger('OptionableDiscovery')
batch_size = 10
class OptionableDiscovery(Collector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  def run(self)->Mapping[str,List[str]]:
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
      except ExdLmtError as error:
        print('Error (sleep 5): '+str(error))
        sleep(5)
        queue.put(instrument)
        continue

    # Publish any remaining items in the buffer
    if len(responses) > 0:
      self.state_store.set_optionable(responses)
    self.state_store.clear_progress(OptionableDiscovery.__name__)
  
  def check_instrument(self, instrument:dict)->bool:
    # Examine the instrument's symbol...
    symbol = instrument['symbol']
    if OptionableDiscovery.has_unlikely_symbol(symbol):
      return None

    # Query the Option Chain...
    chain = self.tdclient.get_options_chain(
      option_chain={
        'symbol':symbol,
        'strikeCount':1})

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
