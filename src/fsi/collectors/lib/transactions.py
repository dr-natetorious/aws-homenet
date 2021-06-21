#!/usr/bin/env python3
from math import ceil, trunc
from lib.interfaces import Collector, RunStatus
from typing import List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from logging import Logger
from time import sleep, strftime
from ratelimitqueue import RateLimitQueue
from lib.StateStore import StateStore
from datetime import date, datetime, timedelta
#from aws_xray_sdk.core import xray_recorder
from datetime import datetime

logger = Logger('OptionableDiscovery')
class TransactionAudit(Collector):
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    super().__init__(tdclient,state_store)

  #@xray_recorder.capture('OptionableDiscovery::run')
  def run(self, lookback_days=7)->RunStatus:
    accounts = self.tdclient.get_accounts()
    queue = RateLimitQueue(calls=30, per=60, fuzz=0.5)
    for account in accounts:
      queue.put(account)

    while queue.qsize() > 0:
      try:
        account = queue.get()
        securitiesAccount = account['securitiesAccount']

        self.state_store.set_account(securitiesAccount, balances={
          'initialBalances': securitiesAccount['initialBalances'] if 'initialBalances' in securitiesAccount else None,
          'currentBalances': securitiesAccount['currentBalances'] if 'currentBalances' in securitiesAccount else None,
          'projectedBalances': securitiesAccount['projectedBalances'] if 'projectedBalances' in securitiesAccount else None,
        })

        transactions = self.tdclient.get_transactions(
          account= securitiesAccount['accountId'],
          start_date=(datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d'),
          end_date= datetime.now().strftime('%Y-%m-%d'),
          transaction_type='ALL')

        if len(transactions) >0:
          self.state_store.add_transactions(securitiesAccount, transactions)
      except ExdLmtError:
        print('API Throttle encountered (sleep 5 seconds)')
        queue.put(account)
        continue

    return RunStatus.COMPLETE