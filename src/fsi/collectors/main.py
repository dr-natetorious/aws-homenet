#!/usr/bin/env python3
from lib.quotes import QuoteCollection
from lib.fundamentals import FundamentalCollection
from os import environ
from lib.ClientFactory import ClientFactory
from lib.StateStore import StateStore
from lib.instruments import InstrumentDiscovery
from lib.optionable import OptionableDiscovery
from lib.transactions import TransactionAudit

if __name__ == "__main__":
  tdclient = ClientFactory.create_client(force_refresh=True)
  state_store = StateStore(
    instrument_table_name=environ.get('INSTRUMENT_TABLE_NAME'),
    transaction_table_name=environ.get('TRANSACTION_TABLE_NAME'),
    quotes_table_name=environ.get('QUOTES_TABLE_NAME'),
    region_name='us-east-2')
  InstrumentDiscovery(tdclient,state_store).run()
  #instruments = state_store.get_instruments()
  #OptionableDiscovery(tdclient, state_store).run()
  #TransactionAudit(tdclient,state_store).run()
  #FundamentalCollection(tdclient,state_store).run()
  # QuoteCollection(tdclient,state_store, candle_config= {
  #   "period_type": "day",
  #   "period": "1",
  #   "frequency_type": "minute",
  #   "frequency": "1"
  # }).run()
