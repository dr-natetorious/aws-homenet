import boto3
from os import path
from io import BytesIO
from json import loads, dumps
from bucket import S3Object
from labels import LabelDocument

class RekClient:
  def __init__(self, region_name:str=None)->None:
    self.__rekognition = boto3.client('rekognition',region_name=region_name)
    self.__s3 = boto3.client('s3', region_name=region_name)

  @property
  def rekognition_client(self)->boto3.client:
    return self.__rekognition

  @property
  def s3_client(self)->boto3.client:
    return self.__s3

  def detect_s3_labels(self, s3_uri:str)->LabelDocument:
    
    s3_object = S3Object.from_s3_uri(s3_uri)

    # Check if this file is already processed
    existing = self.__try_get_s3_labels(s3_object)
    if existing != None:
      return existing

    # Process the image
    response = self.rekognition_client.detect_labels(
      MaxLabels=1000,
      #MinConfidence=55,
      Image={
        'S3Object':{
          'Bucket': s3_object.bucket,
          'Name': s3_object.key
        },
      })

    # Persist the file
    document = LabelDocument(response)
    self.__save_s3_labels(s3_object, document)

    return document

  def __try_get_s3_labels(self, s3_object:S3Object)->LabelDocument:
    response=None
    try:
      response = self.s3_client.get_object(
        Bucket=s3_object.bucket,
        Key='labels/{}.json'.format(s3_object.key))
    except:
      return None

    body = response['Body'].read()
    decode= body.decode()
    props = loads(decode)
    return LabelDocument(props)

  def __save_s3_labels(self, s3_object:S3Object, document:LabelDocument)->None:
    response = self.s3_client.put_object(
      Bucket=s3_object.bucket,
      Key='labels/{}.json'.format(s3_object.key),
      Body = dumps(document.as_dict(), indent=True).encode())

    print('Saved LabelDocument')
    