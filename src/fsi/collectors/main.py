#!/usr/bin/env python3
from lib.ClientFactory import ClientFactory
from lib.StateStore import StateStore
from lib.instruments import InstrumentCollector

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
  state_store = StateStore(table_name='FsiCoreSvc-Collector',region_name='us-east-2')
  InstrumentCollector(tdclient,state_store).run(supported_assetTypes)

#  instruments = fetch_all_instruments(assetTypes=supported_assetTypes)
#  fetch_fundamental_data(instruments)
