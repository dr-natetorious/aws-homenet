from typing import Any, List, Mapping
import boto3
from lib.message import Message

bound_box_precision = 4

class FaceTable:
  def __init__(self, table_name:str, region_name:str) -> None:
    self.dynamodb = boto3.client('dynamodb', region_name=region_name)
    self.table_name = table_name

  def update(self, message:Message)->Mapping[str,Any]:
    
    # Register the KnownFaceId
    try:
      response = self.dynamodb.put_item(
        TableName=self.table_name,
        Item={
          'PartitionKey': {'S':'KnownFaceId'},
          'SortKey': {'S': message.face_id.lower()}
        })
      print(response)
    except Exception as error:
      print(str(error))
      raise error

    # Record the Facial Impression
    try:
      response = self.dynamodb.put_item(
        TableName=self.table_name,
        Item={
          'PartitionKey': {'S': 'FaceId:'+message.face_id.lower()},
          'SortKey': {'S': message.time_stamp},
          's3_uri': {'S': message.s3_uri },
          'camera_name': {'S': message.camera_name.lower() },
          'base_name': {'S': message.base_name.lower() },
          'bounding_box': {'M': 
            {
              'top': { 'N': str(round(message.bounding_box['Top'],bound_box_precision)) },
              'left': { 'N': str(round(message.bounding_box['Left'],bound_box_precision)) },
              'height': { 'N': str(round(message.bounding_box['Height'],bound_box_precision)) },
              'height': { 'N': str(round(message.bounding_box['Width'],bound_box_precision)) },
            }
          }
        })
      print(response)
    except Exception as error:
      print(str(error))
      raise error

