from enum import Enum

class RotationStep(Enum):
  CREATESECRET='CREATESECRET',
  SETSECRET='SETSECRET'
  TESTSECRET='TESTSECRET'
  FINISHSECRET='FINISHSECRET'


class RotationRequest:
  def __init__(self, event:dict) -> None:
    self.__step = RotationStep(event['Step'].upper())
    self.__secretId = event['SecretId']
    self.__client_request_token = event['ClientRequestToken']

  @property
  def step(self)->RotationStep:
    return self.__step

  @property
  def secretId (self)->str:
    return self.__secretId

  @property
  def client_request_token(self)->str:
    return self.__client_request_token