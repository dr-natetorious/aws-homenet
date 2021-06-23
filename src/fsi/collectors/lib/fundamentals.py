#!/usr/bin/env python3
from lib.interfaces import Collector, QueuedCollector, RunStatus
from typing import Any, List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore

logger = Logger('FundamentalCollection')
class FundamentalCollection(QueuedCollector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  def process_instrument(self,instrument:dict)->Any:
    """
    Examine the instrument's symbol
    """
    symbol = instrument['symbol']
    if Collector.is_garbage_symbol(symbol):
      return None

    # Query the Fundamental data
    is_success = False
    for attempt in range(1,3):
      try:
        response = self.tdclient.search_instruments(
          symbol=symbol,
          projection='fundamental')
        is_success = True
        break
      except Exception as error:
        logger.error(str(error))
        sleep(attempt * attempt)
        raise error

    # Validate the response is valid
    if is_success == False:
      raise GeneralError(
        'Unable to get_options_chain(symbol={}) within 3 attempts.'.format(symbol))

    if response == None:
      return None
    if symbol not in response:
      return None
    if 'fundamental' not in response[symbol]:
      return None
    
    # Normalize and flatten
    fundamental = response[symbol]['fundamental']
    StateStore.normalize(fundamental)
    for key in ['cusip', 'description','exchange','assetType']:
      fundamental[key] = response[key] if key in response else 'N/A'
    return fundamental
    
  def persist_batch(self,batch:List[Any])->None:
    self.state_store.set_fundamentals(batch)