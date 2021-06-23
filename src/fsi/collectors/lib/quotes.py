#!/usr/bin/env python3
from lib.interfaces import Collector, QueuedCollector, RunStatus
from typing import Any, List, Mapping
from td.client import TDClient
from logging import Logger
from time import sleep
from lib.StateStore import StateStore
from decimal import Decimal

logger = Logger('FundamentalCollection')
class QuoteCollection(QueuedCollector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  def process_instrument(self,instrument:dict)->List[Mapping[str,Decimal]]:
    symbol = instrument['symbol']
    response = Collector.attempt_with_retry(
      action=lambda: self.tdclient.get_price_history(
        symbol=symbol,
        period_type='day',
        period='1',
        frequency_type='minute',
        frequency='1'
      ))

    if response == None:
      return None

    candles = response['candles']
    for candle in candles:
      candle['symbol'] = symbol
      candle['frequency_type'] = 'minute'
      candle['frequency_size'] = 1
      candle['period_type']='day'
      candle['period']=1
      StateStore.normalize(candle)

    return candles

  def persist_batch(self,batch:List[Mapping[str,Decimal]])->None:
  #def persist_batch(self,batch:List[Any])->None:
    self.state_store.set_quotes(batch)