#!/usr/bin/env python3
import boto3
#from Collector import fetch_all_instruments, fetch_quotes_data

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
  # try:
  #   request = client.create_changeset(
  #     datasetId='esp38x1',
  #     changeType='APPEND',
  #     sourceParams={
  #       'SPY': 's3://homenet-coresvc.us-east-2.trader.fsi/data/split/SPY.csv'
  #     },
  #     sourceType='S3',
  #     formatType='CSV'
  #   )
  #   print(request)
  # except Exception as error:
  #   print(error)
  #   raise error
  # #instruments = fetch_all_instruments(assetTypes=supported_assetTypes)
  # #fetch_quotes_data(instruments)
