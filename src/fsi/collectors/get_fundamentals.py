#!/usr/bin/env python3
from Collector import fetch_all_instruments, fetch_fundamental_data

supported_assetTypes = [
  "EQUITY",
  "ETF",
  "FOREX",
  "FUTURE",
  "FUTURE_OPTION",
  "INDEX",
  "INDICATOR",
  "MUTUAL_FUND",
  "OPTION",
  "UNKNOWN"
]

if __name__ == "__main__":  
  instruments = fetch_all_instruments(assetTypes=supported_assetTypes)
  fetch_fundamental_data(instruments)
