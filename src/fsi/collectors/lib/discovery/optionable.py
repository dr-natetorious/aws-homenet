#!/usr/bin/env python3
from math import ceil
from lib.interfaces import  QueuedCollector
from lib.enums import  SecurityStatus
from typing import Any, List, Mapping
from td.client import TDClient
from logging import Logger
from time import sleep
from lib.StateStore import StateStore

#from aws_xray_sdk.core import xray_recorder

logger = Logger('OptionableDiscovery')
class OptionableDiscovery(QueuedCollector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  @property
  def batch_size(self) -> int:
    return 25

  def fetch_known_instruments(self) -> List[dict]:
    """
    Discover equities that are Normal or Halted
    """
    return self.state_store.retrieve_equities(
      filter_status=SecurityStatus.standard_ignore_list())

  def process_instrument(self,instrument:dict)->Any:
    """
    Examine the instrument's symbol
    """
    symbol = instrument['symbol']
    chain = OptionableDiscovery.attempt_with_retry(
      action=lambda: self.tdclient.get_options_chain(
        option_chain={
          'symbol':symbol,
          'strikeCount':1
        }))

    if chain == None:
      return None

    # Return the query results...
    return {
      'symbol': symbol,
      'exchange': instrument['exchange'],
      'securityStatus': instrument['securityStatus'],
      'is_optionable': chain['status'] == 'SUCCESS',
      'numberOfContracts': ceil(StateStore.default_value(chain,'numberOfContracts',0)),
      'volatility': ceil(StateStore.default_value(chain,'volatility',0)),
      'isIndex': StateStore.default_value(chain,'isIndex',False),
      'isDelayed': StateStore.default_value(chain,'isDelayed',False)
    }

  def persist_batch(self,batch:List[Any])->None:
    self.state_store.set_optionable(batch)
