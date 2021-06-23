#!/usr/bin/env python3
from math import ceil, trunc
from lib.interfaces import Collector, QueuedCollector, RunStatus
from typing import Any, List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore
from datetime import datetime
#from aws_xray_sdk.core import xray_recorder

logger = Logger('OptionableDiscovery')
batch_size = 25
class OptionableDiscovery(QueuedCollector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  def process_instrument(self,instrument:dict)->Any:
    """
    Examine the instrument's symbol
    """
    symbol = instrument['symbol']
    if Collector.is_garbage_symbol(symbol):
      return None

    # Query the Option Chain...
    is_success = False
    for attempt in range(1,3):
      try:
        chain = self.tdclient.get_options_chain(
          option_chain={
            'symbol':symbol,
            'strikeCount':1})
        is_success = True
        break
      except Exception as error:
        logger.error(str(error))
        sleep(attempt * attempt)
        raise error

    if is_success == False:
      raise GeneralError(
        'Unable to get_options_chain(symbol={}) within 3 attempts.'.format(symbol))

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

  def persist_batch(self,batch:List[Any])->None:
    self.state_store.set_optionable(batch)
