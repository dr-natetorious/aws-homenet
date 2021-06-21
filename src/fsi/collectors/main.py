#!/usr/bin/env python3
from os import environ
from lib.ClientFactory import ClientFactory
from lib.StateStore import StateStore
from lib.instruments import InstrumentDiscovery
from lib.optionable import OptionableDiscovery
from lib.transactions import TransactionAudit

supported_assetTypes = [
  "EQUITY",
  "ETF",
  "FOREX",
  "FUTURE",
  "FUTURE_OPTION",
  "INDEX",
  "INDICATOR",
  # "MUTUAL_FUND",
  "OPTION",
  # "UNKNOWN"
]


if __name__ == "__main__":
  tdclient = ClientFactory.create_client(force_refresh=True)
  state_store = StateStore(
    instrument_table_name=environ.get('INSTRUMENT_TABLE_NAME'),
    transaction_table_name=environ.get('TRANSACTION_TABLE_NAME'),
    region_name='us-east-2')
  #InstrumentDiscovery(tdclient,state_store).run(supported_assetTypes)
  #instruments = state_store.get_instruments()
  #OptionableDiscovery(tdclient, state_store).run()
  TransactionAudit(tdclient,state_store).run()


#  instruments = fetch_all_instruments(assetTypes=supported_assetTypes)
#  fetch_fundamental_data(instruments)
