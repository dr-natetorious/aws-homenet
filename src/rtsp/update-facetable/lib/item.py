from typing import Any, List, Mapping
import boto3
from enum import Enum
from lib.message import Message

class AttributeType(Enum):
  STRING='S'
  NUMBER='N'
  BYTES='B'
  STRING_SET='SS'
  NUMBER_SET='NS'
  BYTE_SET='BS'
  MAP='M'
  BOOLEAN='BOOL'
  NULL='NULL'

class Attribute:
  def __init__(self, name:str, value:Any, value_type:AttributeType=AttributeType.STRING) -> None:
    self.__name = name
    self.__value = value
    self.__value_type = value_type

  @property
  def name(self)->str:
    return self.__name

  @property
  def value(self)->str:
    return self.__value

  @property
  def value_type(self)->AttributeType:
    return self.__value_type

class Item:
  def __init__(self, partition_key:str, sort_key:str, attributes:List[Attribute]=None) -> None:
    assert partition_key != None, "Missing partition_key"
    assert sort_key != None, "Missing sort key"

    self.__partition_key = partition_key
    self.__sort_key = sort_key

    if attributes == None:
      attributes=[]

    attributes.append(Attribute('PartitionKey',self.partition_key))
    attributes.append(Attribute('SortKey',self.sort_key))

    self.__attributes = attributes

  @property
  def partition_key(self)->str:
    return self.__partition_key

  @property
  def sort_key(self)->str:
    return self.__sort_key

  @property
  def attributes(self)->List[Attribute]:
    return self.__attributes

  def as_dict(self)->Mapping[str,Mapping[str,Any]]:
    item = {}
    for attribute in self.attributes:
      item[attribute.name] = {
        attribute.value_type.value : attribute.value
      }
    return item
    
