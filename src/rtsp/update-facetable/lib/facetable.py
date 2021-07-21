from typing import Any, List, Mapping
import boto3
from lib.message import Message

precision = 4

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
          'sharpness': {'N': str(round(message.quality['Sharpness'], precision))},
          'brightness': {'N': str(round(message.quality['Brightness'], precision))},
          'confidence': {'N': str(round(message.confidence, precision))},
          'bounding_box': {'M': 
            {
              'top': { 'N': str(round(message.bounding_box['Top'],precision)) },
              'left': { 'N': str(round(message.bounding_box['Left'],precision)) },
              'height': { 'N': str(round(message.bounding_box['Height'],precision)) },
              'width': { 'N': str(round(message.bounding_box['Width'],precision)) },
            }
          }
        })
      print(response)
    except Exception as error:
      print(str(error))
      raise error

