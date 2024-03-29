#!/usr/bin/env python3
from lib.quotes import HistoricQuoteCollection
from lib.point_in_time.fundamentals import FundamentalCollection
from lib.point_in_time.options import OptionsCollection
from os import environ
from lib.ClientFactory import ClientFactory
from lib.StateStore import StateStore
from lib.discovery.instruments import InstrumentDiscovery
from lib.discovery.optionable import OptionableDiscovery
from lib.transactions import TransactionAudit

if __name__ == "__main__":
  tdclient = ClientFactory.create_client(force_refresh=True)
  state_store = StateStore(
    instrument_table_name=environ.get('INSTRUMENT_TABLE_NAME'),
    transaction_table_name=environ.get('TRANSACTION_TABLE_NAME'),
    quotes_table_name=environ.get('QUOTES_TABLE_NAME'),
    options_table_name=environ.get('OPTIONS_TABLE_NAME'),
    region_name='us-east-2')
  #InstrumentDiscovery(tdclient,state_store).run()
  #instruments = state_store.get_instruments()
  #OptionableDiscovery(tdclient, state_store).run()
  #TransactionAudit(tdclient,state_store).run()
  #FundamentalCollection(tdclient,state_store).run()
  OptionsCollection(tdclient,state_store).run()
  # QuoteCollection(tdclient,state_store, candle_config= {
  #   "period_type": "day",
  #   "period": "1",
  #   "frequency_type": "minute",
  #   "frequency": "1"
  # }).run()
