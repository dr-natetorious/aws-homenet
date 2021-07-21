from typing import List
from json import loads

class Emotion:
  def __init__(self, props:dict) -> None:
    self.__confidence = props['Confidence']
    self.__type = props['Type']

  @property
  def confidence(self)->float:
    return self.__confidence

  @property
  def type(self)->str:
    return self.__type

class Message:
  """
  Represents the SnsNotifications payload. 
  """
  def __init__(self, props:dict) -> None:
    self.__props = props
    self.__time_stamp = props['Sns']['Timestamp']
    self.__parse_payload(loads(props['Sns']['Message']))

  def __parse_payload(self, props:dict)->None:
    self.__face_id = props['FaceId']
    self.__image_id=  props['ImageId']
    self.__bounding_box=  props['BoundingBox']
    self.__confidence=  props['Confidence']
    self.__age_range=  props['Age']
    self.__gender=  props['Gender']
    self.__emotions=  [Emotion(x) for x in props['Emotions']]
    self.__quality=  props['Quality']
    self.__camera = props['Camera']
    self.__s3_uri = props['S3_Uri']
    self.__base_name = props['BaseName']

  def as_dict(self)->dict:
    return self.__props

  @property
  def time_stamp(self)->str:
    return self.__time_stamp

  @property
  def face_id(self)->str:
    return self.__face_id

  @property
  def image_id(self)->str:
    return self.__image_id

  @property
  def bounding_box(self)->dict:
    return self.__bounding_box

  @property
  def confidence(self)->dict:
    return self.__confidence

  @property
  def age_range(self)->dict:
    return self.__age_range

  @property
  def gender(self)->dict:
    return self.__gender

  @property
  def emotions(self)->List[Emotion]:
    return self.__emotions

  @property
  def quality(self)->dict:
    return self.__quality

  @property
  def camera_name(self)->str:
    return self.__camera

  @property
  def base_name(self)->str:
    return self.__base_name

  @property
  def s3_uri(self)->str:
    return self.__s3_uri

  def filter_emotions(self,threshold:float=60.0)->List[str]:
    """
    Filter low confidence predictions
    """
    results=[]
    for emotion in self.emotions:
      if emotion.confidence >= threshold:
        results.append(emotion.type)
    return results

