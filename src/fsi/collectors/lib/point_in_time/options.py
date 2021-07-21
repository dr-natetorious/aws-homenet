#!/usr/bin/env python3
from decimal import Decimal
from math import ceil
import re

from lib.interfaces import  QueuedCollector
from typing import Any, List
from td.client import TDClient
from logging import Logger
from lib.StateStore import StateStore

logger = Logger('OptionCollection')
class OptionsCollection(QueuedCollector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  @property
  def batch_size(self) -> int:
    return 5

  def fetch_known_symbols(self)->List[dict]:
    """
    Discover equities that are Normal or Halted
    """
    instruments = self.state_store.retrieve_optionable()

    filtered = [
      inst for inst in instruments 
      if not inst['exchange'] == 'Pink Sheet'
    ]

    print('OptionsCollection.fetch_known_symbols() filtering {} into {} instruments'.format(
      len(instruments),
      len(filtered)
    ))

    return filtered

  def process_instrument(self,instrument:dict)->Any:
    """
    Examine the instrument's symbol
    """
    symbol = instrument['symbol']
    chain = OptionsCollection.attempt_with_retry(
      action=lambda: self.tdclient.get_options_chain(
        option_chain={
          'symbol':symbol,
        }))

    if chain == None:
      return None

    header = {
      'symbol': symbol,
      'is_optionable': chain['status'] == 'SUCCESS',
      'interestRate': chain['interestRate'],
      'underlyingPrice': chain['underlyingPrice'],
      'volatility': chain['volatility']
    }

    contracts = []
    for contractMap in ['callExpDateMap', 'putExpDateMap']:
      contractMap = chain[contractMap]
      for series in contractMap.keys():
        split = series.split(':')
        expiration = split[0]
        dte = split[1]
        for strike in contractMap[series].keys():
          if len(contractMap[series][strike]) > 1:
            logger.debug('Skipping micro-contract in {}'.format(symbol))

          contract:dict = contractMap[series][strike][0]
          contract['id'] = contract['symbol']
          contract['strike'] = Decimal(strike)
          contract['series'] = expiration
          contract.update(header)

          StateStore.normalize(contract)
          contracts.append(contract)


    # Return the query results...
    return contracts

  def persist_batch(self,batch:List[List[dict]])->None:
    self.state_store.set_option_chains(batch)
