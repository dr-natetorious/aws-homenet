#!/usr/bin/env python3
from lib.interfaces import Collector, RunStatus
from typing import List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore

logger = Logger('InstrumentDiscovery')
class InstrumentDiscovery(Collector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  def run(self)->RunStatus:
    """
    Enumerates through all symbols
    """
    symbols = {}
    filter_count=0
    queue = RateLimitQueue(calls=100, per=60, fuzz=0.5)
    for alpha in list(range(65,91)) + list(range(48,57)):
      prefix = '.*'+chr(alpha)
      queue.put(prefix)

    while(queue.qsize() > 0):  
      try:
        prefix = queue.get()
        instruments = self.tdclient.search_instruments(
          symbol=prefix,
          projection='symbol-regex')
      except ExdLmtError as error:
        print('Error (sleep 10sec): '+str(error))
        queue.put(prefix)
        sleep(10)
        continue
      except GeneralError:
        # Response too big, split into subcalls...
        print('Response too big - {}; splitting...'.format(prefix))
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

      self.state_store.declare_instruments(list(instruments.values()))

      for symbol in instruments.keys():
        assetType = instruments[symbol]['assetType']
        if not assetType in symbols:
          symbols[assetType] = [symbol]
        else:
          symbols[assetType].append(symbol)      

    print('SUMMARY: {} instruments with {} filtered...'.format(
      [{str(x):len(symbols[x])} for x in symbols.keys()], filter_count))
    
    return RunStatus.COMPLETE