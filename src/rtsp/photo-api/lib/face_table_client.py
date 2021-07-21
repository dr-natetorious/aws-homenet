from typing import List, Mapping
import boto3
from botocore.exceptions import ValidationError

class KnownIdentity:
  def __init__(self, props) -> None:
    self.__alias = props['SortKey'].lower()
    self.__display_name = props['display_name']
    self.__props = props

  @property
  def alias(self)->str:
    return self.__alias

  @property
  def display_name(self)->str:
    return self.__display_name

  def as_dict(self)->dict:
    return self.__props

  @staticmethod
  def from_dynamodb_item(item:dict):
    results = {
      'SortKey': item['SortKey']['S'],
      'display_name': item['display_name']['S']
    }
    return KnownIdentity(results)

class FaceTableClient:
  def __init__(self, face_table_name:str, region_name:str) -> None:
    assert face_table_name != None, "No table name provided"

    self.__face_table_name = face_table_name
    self.dynamodb = boto3.client('dynamodb', region_name=region_name)

  @property
  def face_table_name(self)->str:
    return self.__face_table_name

  def get_identities(self)->List[KnownIdentity]:
    response = self.dynamodb.query(
      TableName=self.face_table_name,
      Select='ALL_ATTRIBUTES',
      Limit=1000,
      ReturnConsumedCapacity='NONE',
      KeyConditionExpression="PartitionKey= :partitionKey",
      ExpressionAttributeValues={
        ":partitionKey": {'S': 'Identity'},
      })
    return [KnownIdentity.from_dynamodb_item(x) for x in response['Items']]

  def get_known_faces(self)->Mapping[str,List[str]]:
    response = self.dynamodb.query(
      TableName=self.face_table_name,
      Select='ALL_ATTRIBUTES',
      Limit=1000,
      ReturnConsumedCapacity='NONE',
      KeyConditionExpression="PartitionKey= :partitionKey",
      ExpressionAttributeValues={
        ":partitionKey": {'S': 'KnownFaceId'},
      })

    return {
      'KnownFaces': [x['SortKey']['S'] for x in response['Items']]
    }

  def register_identity(self, request:KnownIdentity)->dict:
    return self.dynamodb.put_item(
      TableName=self.face_table_name,
      Item={
        'PartitionKey': {'S': 'Identity'},
        'SortKey': {'S': request.alias},
        'display_name': {'S': request.display_name},
      })

  def identify_faceid(self,identity:str, face_id:str)->dict:
    if identity == None:
      raise ValidationError('identity')
    if face_id == None:
      raise ValidationError('face_id')
    
    self.dynamodb.put_item(
      TableName=self.face_table_name,
      Item={
        'PartitionKey': {'S': 'Identity::'+identity.lower()},
        'SortKey': {'S': face_id.lower()},
      })

  def get_face_images(self, face_id:str)->dict:
    response = self.dynamodb.query(
      TableName=self.face_table_name,
      Select='ALL_ATTRIBUTES',
      Limit=1000,
      ReturnConsumedCapacity='NONE',
      KeyConditionExpression="PartitionKey= :partitionKey",
      ExpressionAttributeValues={
        ":partitionKey": {'S': 'FaceId:'+face_id.lower()},
      })

    return {
      'FaceId': face_id,
      'Images': [{
        's3_uri': x['s3_uri']['S'],
        'timestamp': x['SortKey']['S'],
        'bounding_box': FaceTableClient.__extract_bounding_box(x),
        'quality': {
          'sharpness': x['sharpness']['N'] if 'sharpness' in x else 0,
          'brightness': x['brightness']['N'] if 'brightness' in x else 0,
          'confidence': x['confidence']['N'] if 'confidence' in x else 0,
        }
      } for x in response['Items']]
    }

  @staticmethod
  def __extract_bounding_box(x):
    result = {}
    if not 'bounding_box' in x:
      return result

    x = x['bounding_box']['M']
    result['height'] = x['height']['N'] if 'height' in x else 0
    result['width'] = x['width']['N'] if 'width' in x else 0
    result['top'] = x['top']['N'] if 'top' in x else 0
    result['left'] = x['left']['N'] if 'left' in x else 0
    return result
    