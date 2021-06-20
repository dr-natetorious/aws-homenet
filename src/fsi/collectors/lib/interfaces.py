import logging
from typing import List, Mapping
from td.client import ExdLmtError, TDClient
from td.exceptions import GeneralError
from lib.ClientFactory import ClientFactory
from os import environ
from json import dumps
from logging import getLogger
from time import sleep
from ratelimitqueue import RateLimitQueue
import boto3
from os import environ
from base64 import b64encode
from uuid import uuid1
from lib.StateStore import StateStore

class Collector:
  def __init__(self, tdclient:TDClient, state_store:StateStore) -> None:
    assert tdclient != None, "No tdclient"
    assert state_store != None, "No state store"

    self.__tdclient= tdclient
    self.__state_store = state_store

  @property
  def tdclient(self)->TDClient:
    return self.__tdclient

  @property
  def state_store(self)->TDClient:
    return self.__state_store

  def run(self)->None:
    raise NotImplementedError()