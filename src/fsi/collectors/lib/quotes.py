#!/usr/bin/env python3
from lib.interfaces import Collector, QueuedCollector, RunStatus
from typing import Any, List, Mapping
from td.client import TDClient
from logging import Logger
from time import sleep
from lib.StateStore import StateStore
from decimal import Decimal
from logging import Logger

logger = Logger(name='QuoteCollection')

class CandleConfiguration:
  def __init__(self, props:dict=None) -> None:
    if props == None:
      props = {}

    logger.debug('Input: CandleConfig: {}' % props)
    self.period_type=str(StateStore.default_value(props,'period','day'))
    self.period=str(StateStore.default_value(props,'period','1'))
    self.frequency_type=str(StateStore.default_value(props, 'frequency_type','minute'))
    self.frequency=str(StateStore.default_value(props, 'frequency','1'))

    logger.info('Init: CandleConfiguration: {}'.format(str(self)))

  def to_dict(self)->dict:
    return {
      'period_type': self.period_type,
      'period': self.period,
      'frequency_type': self.frequency_type,
      'frequency': self.frequency
    }

  def __str__(self)->str:
    return str(self.to_dict())

logger = Logger('FundamentalCollection')
class QuoteCollection(QueuedCollector):
  def __init__(self, tdclient:TDClient, state_store:StateStore, candle_config:CandleConfiguration) -> None:
    super().__init__(tdclient,state_store)
    
    if not type(candle_config) == CandleConfiguration:
      candle_config = CandleConfiguration(candle_config)
    
    self.candle_config = candle_config

  def process_instrument(self,instrument:dict)->List[Mapping[str,Decimal]]:
    symbol = instrument['symbol']
    response = Collector.attempt_with_retry(
      action=lambda: self.tdclient.get_price_history(
        symbol=symbol,
        period_type=self.candle_config.period_type,
        period=self.candle_config.period,
        frequency_type=self.candle_config.frequency_type,
        frequency=self.candle_config.frequency
      ))

    if response == None:
      return None
    if StateStore.default_value(response,'empty',False):
      return None

    candles = response['candles']
    for candle in candles:
      candle['symbol'] = symbol
      candle['frequency_type'] = self.candle_config.frequency_type
      candle['frequency'] = int(self.candle_config.frequency)
      candle['period_type']=self.candle_config.period_type
      candle['period']=int(self.candle_config.period)
      StateStore.normalize(candle)

    return candles

  def persist_batch(self,batch:List[Mapping[str,Decimal]])->None:
  #def persist_batch(self,batch:List[Any])->None:
    self.state_store.set_quotes(batch)