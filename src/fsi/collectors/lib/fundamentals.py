#!/usr/bin/env python3
from lib.interfaces import Collector, QueuedCollector, RunStatus
from typing import Any, List
from td.client import TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep
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

    # Query the Fundamental data
    response = Collector.attempt_with_retry(
      action=lambda: self.tdclient.search_instruments(
        symbol=symbol,
        projection='fundamental'))

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