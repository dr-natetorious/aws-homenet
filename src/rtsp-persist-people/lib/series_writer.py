from datetime import datetime
from logging import Logger
from dateutil.tz import tzutc
from dateutil.parser import isoparse
from json import dumps
from typing import Any, List, Mapping
import boto3
from enum import Enum

epoch = datetime.utcfromtimestamp(0).replace(tzinfo=tzutc())

class ValueType(Enum):
  VARCHAR = 'VARCHAR'
  DOUBLE = 'DOUBLE'
  BIGINT = 'BIGINT'
  BOOLEAN = 'BOOLEAN'

class TimeUnit(Enum):
  MILLISECONDS='MILLISECONDS'
  SECONDS='SECONDS'
  MICROSECONDS='MICROSECONDS'
  NANOSECONDS='NANOSECONDS'

class DataPoint:
  def __init__(self, name:str, value:str, value_type:ValueType) -> None:
    assert name != None, "Missing name"
    assert value != None, "Missing value"
    assert name != None, "Missing value_type"

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
  def value_type(self)->ValueType:
    return self.__value_type

  def as_dict(self)->Mapping[str,str]:
    raise NotImplemented()    

class Dimension(DataPoint):
  def __init__(self, name:str, value:str) -> None:
    super().__init__(name=name,value=value,value_type=ValueType.VARCHAR)

  def as_dict(self) -> Mapping[str,str]:
    return {
      'Name': self.name,
      'Value': self.value,
      'DimensionValueType': self.value_type.value
    }

class Measurement(DataPoint):
  def __init__(self, name:str, value:str, value_type:ValueType) -> None:
    super().__init__(name=name,value=str(value),value_type=value_type)

  def as_dict(self) -> Mapping[str,str]:
    return {
      'Name': self.name,
      'Value': self.value,
      'MeasureValueType': self.value_type.value
    }

class TimeStamp:
  def __init__(self, value:datetime) -> None:
    assert value != None, "Missing time_stamp.value"
    self.__value = value

  @property
  def value(self)->datetime:
    return self.__value

class Record:
  def __init__(self, measurement:Measurement=None, time_stamp:TimeStamp=None, dimensions:List[Dimension]=None, version:int=None) -> None:
    self.__measurement = measurement
    self.__time_stamp = time_stamp
    self.__dimensions = dimensions
    self.__version = version

  @property
  def measurement(self)->Measurement:
    return self.__measurement

  @property
  def time_stamp(self)->TimeStamp:
    return self.__time_stamp
  
  @property
  def dimensions(self)->List[Dimension]:
    return self.__dimensions

  @property
  def version(self)->int:
    return self.__version

  def as_dict(self)->Mapping[str,Any]:
    result= {}
  
    if self.measurement != None:
      result['MeasureName']= self.measurement.name
      result['MeasureValue']= self.measurement.value
      result['MeasureValueType']= self.measurement.value_type.value

    if self.version != None:
      result['Version']= self.version
    
    if self.dimensions != None:
      result['Dimensions']= [d.as_dict() for d in self.dimensions]
      
    if self.time_stamp != None:
      time = (self.time_stamp.value - epoch).total_seconds() * 1000
      result['Time']= str(int(time))
      result['TimeUnit']=TimeUnit.MILLISECONDS.value

    return result

class TableName:
  def __init__(self, database_name:str, table_name:str)  -> None:
    assert database_name != None, "Missing database_name"
    assert table_name != None, "Missing table_name"

    self.__database_name = database_name
    self.__table_name = table_name

  @property
  def database_name(self)->str:
    return self.__database_name

  @property
  def table_name(self)->str:
    return self.__table_name

  @property
  def table_uri(self)->str:
    return 'timestream://{}/{}'.format(
      self.database_name,
      self.table_name)


class WriteRecordsRequest:
  """
  Represents a request to write into the Amazon Timestream table
  """
  def __init__(self, table:TableName, common_attributes:Record=None, records:List[Record]=None) -> None:
    assert table != None, "Missing table"
    
    self.__table = table
    self.__common_attributes = common_attributes

    if records == None:
      records = []
    self.__records = records

  @property
  def table(self)->TableName:
    return self.__table

  @property
  def common_attributes(self)->Record:
    return self.__common_attributes

  @property
  def records(self)->List[Record]:
    return self.__records

  def add_record(self, record:Record)->None:
    if record != None:
      self.__records.append(record)

  def add_records(self, records:List[Record])->None:
    if records != None:
      for record in records:
        self.add_record(record)

  def as_dict(self)->Mapping[str,Any]:
    result = {
      'DatabaseName': self.table.database_name,
      'TableName': self.table.table_name,
    }

    if self.common_attributes != None:
      result['CommonAttributes']= self.common_attributes.as_dict()

    if self.records != None:
      result['Records']= [r.as_dict() for r in self.records]

    return result

class SeriesWriter:
  """
  Represents a utility for writing into Amazon Timestream.
  """
  def __init__(self, region_name:str) -> None:
    self.__client= boto3.client('timestream-write', region_name=region_name)
    self.__logger = Logger(name=SeriesWriter.__name__)

  @property
  def client(self)->boto3.client:
    return self.__client

  @property
  def logger(self)->Logger:
    return self.__logger

  def write_records(self,request:WriteRecordsRequest)->Mapping[str,Any]:
    try:
      self.logger.info('Sending Request to {} with {} records'.format(
        request.table.table_uri,
        len(request.records)
      ))
      
      return self.client.write_records(
        DatabaseName=request.table.database_name,
        TableName=request.table.table_name,
        CommonAttributes=request.common_attributes.as_dict(),
        Records= [r.as_dict() for r in request.records])
    except Exception as error:
      self.logger.error('Writing to {} failed with {}'.format(
        request.table.table_uri,
        error))

      self.logger.error(dumps(request.as_dict(), indent=2))
      raise error
