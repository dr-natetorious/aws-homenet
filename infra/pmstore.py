#!/usr/bin/env python3
import os.path
from datetime import datetime
from typing import List
from aws_cdk import (
    core,
    aws_ssm as ssm,
    custom_resources as cr,
)

src_root_dir = os.path.join(os.path.dirname(__file__))

class ParameterReaderProps:
  def __init__(self, parameterName:str, region:str, with_decryption:bool=True)->None:
    self.__parameterName = parameterName
    self.__region = region
    self.__with_decryption = with_decryption

  @property
  def parameterName(self)->str:
    return self.__parameterName

  @property
  def region(self)->str:
    return self.__region

  @property
  def with_decryption(self)->bool:
    return self.__with_decryption

class ParameterReader(core.Construct):
  def __init__(self,scope:core.Construct, id:str, props:ParameterReaderProps, **kwargs) ->None:
    super().__init__(scope, id, **kwargs)

    self.resource = cr.AwsCustomResource(self,'get_parameters',
      policy= cr.AwsCustomResourcePolicy.from_sdk_calls(
        resources= cr.AwsCustomResourcePolicy.ANY_RESOURCE),
      on_update=cr.AwsSdkCall(
        service='SSM',
        action='getParameter',
        parameters={
          'Name': props.parameterName,
          'WithDecryption':props.with_decryption,
        },
        region= props.region,
        physical_resource_id= cr.PhysicalResourceId.of(id=str(datetime.now()))
        ))

  @property
  def value(self)->str:
    return str(self.resource.get_response_field('Parameter.Value'))
    
