from typing import Any, List, Mapping
import boto3
from lib.message import Message

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
          'SortKey': {'S': message.face_id}
        })
      print(response)
    except Exception as error:
      print(error)

    # Record the Facial Impression
    try:
      response = self.dynamodb.put_item(
        TableName=self.table_name,
        Item={
          'PartitionKey': {'S': 'FaceId:'+message.face_id},
          'SortKey': {'S': message.time_stamp},
          's3_uri': {'S': message.s3_uri},
          'camera_name': {'S': message.camera_name },
        })
      print(response)
    except Exception as error:
      print(error)
