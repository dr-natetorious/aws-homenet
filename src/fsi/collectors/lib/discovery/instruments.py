#!/usr/bin/env python3
from lib.enums import SecurityStatus
from lib.interfaces import  Collector, QueuedCollector
from typing import Any, List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore

logger = Logger('InstrumentDiscovery')
class InstrumentDiscovery(QueuedCollector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  @property
  def batch_size(self) -> int:
    return 5

  def create_symbol_queue_from_marker(self) -> RateLimitQueue:
    marker = self.get_progress_marker()

    self.queue = RateLimitQueue(calls=60, per=60, fuzz=0.5)
    for alpha in list(range(65,91)) + list(range(48,57)):
      suffix = '.*'+chr(alpha)
      if suffix < marker:
        continue

      self.queue.put({'symbol':suffix})
    return self.queue

  def choose_progress_marker_from_batch(self, instrument, batch: list) -> str:
    return instrument['symbol']

  def process_instrument(self,instrument:dict)->List[Mapping[str,Any]]:
    symbol = instrument['symbol']
    try:
      instruments = self.tdclient.search_instruments(
        symbol=symbol,
        projection='symbol-regex')
    except GeneralError:
      # Response too big, split into subcalls...
      print('Response too big - {}; splitting...'.format(symbol))
      suffix = symbol[-1].replace('.*','')
      
      #self.queue.put({'symbol':symbol})
      for ch in list(range(65,91)) + list(range(48,57)):
        prefix = '.*{}{}'.format(chr(ch),suffix)
        self.queue.put({'symbol':prefix})
      return None
    
    print('annotate_invalid_instruments(instruments=%d)' % len(instruments))
    self.annotate_invalid_instruments(instruments)
    return list(instruments.values())

  def persist_batch(self,batch:List[Mapping[str,Any]])->None:
    self.state_store.declare_instruments(batch)

  def annotate_invalid_instruments(self, instruments:Mapping[str,Any])->None:
    valid_tasks = []
    ignored_index=[]
    garbage_symbols=[]
    for symbol, instrument in instruments.items():
      # There's a ton of $NQ***X that doesn't actually exist?
      # TODO: This disables support for index funds and needs future consideration
      if symbol.startswith('$'):
        instrument['securityStatus'] = SecurityStatus.NONE.name
        ignored_index.append(symbol)
        continue
      
      # Just ignore anything that looks sus'
      if Collector.is_garbage_symbol(symbol):
        instrument['securityStatus'] = SecurityStatus.NONE.name
        garbage_symbols.append(symbol)
        continue
      
      # Add the task
      valid_tasks.append(instrument)

    if len(ignored_index) > 0:
      print('Defaulted {} index instruments (e.g., {}) to None'.format(
        len(ignored_index),
        ignored_index[0] ))

    if len(garbage_symbols) > 0:
      print('Defaulted {} garbage instruments (e.g., {}) to None'.format(
        len(garbage_symbols),
        garbage_symbols[0] ))
    
    # Setting chunk size too high overflows in get_quotes buffer
    # TDA services responds with HttpStatus=400 and no error message
    tasks = RateLimitQueue(calls=60, per=60, fuzz=0.5)
    for chunk in InstrumentDiscovery.chunks(list(valid_tasks), 500):
      tasks.put(chunk)
    
    while tasks.qsize() > 0:
      try:
        chunk = tasks.get()
        print('Attempting [offset: {} | chuck size: {} | len: {}]'.format(
          StateStore.default_value(chunk[0], 'symbol', {'symbol:':'THE END'}),
          len(chunk),
          sum([len(x['symbol']) for x in chunk])
        ))
        quotes = InstrumentDiscovery.attempt_with_retry(
          action=lambda: self.tdclient.get_quotes(
            instruments=[x['symbol'] for x in chunk]))

        for key, value in quotes.items():
          securityStatus = value['securityStatus']
          
          # These seem to require inline datafixer...
          if securityStatus == key and value['exchangeName'] == 'BATS':
            securityStatus = 'Normal'

          if not securityStatus in ['Normal','Unknown','Closed','None','Halted','Deleted']:
            securityStatus = 'NotImplemented'

          instruments[key]['securityStatus'] = securityStatus.upper()
          
      except NotImplementedError as error:
        raise error
      

  @staticmethod
  def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
      yield lst[i:i + n]