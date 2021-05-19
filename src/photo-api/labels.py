from typing import List

class BoundingBox:
  def __init__(self, props:dict)->None:
    self.__width = props['Width']
    self.__height = props['Height']
    self.__left = props['Left']
    self.__top = props['Top']

  @property
  def width(self)->float:
    return self.__width

  @property
  def height(self)->float:
    return self.__height

  @property
  def left(self)->float:
    return self.__left

  @property
  def top(self)->float:
    return self.__top

class ParentLabel:
  def __init__(self, props:dict)->None:
    self.__name = props['Name']

  @property
  def name(self)->str:
    return self.__name

class LabelInstance:
  def __init__(self, props:dict)->None:
    if 'BoundingBox' in props:
      self.__bounding_box = BoundingBox(props['BoundingBox'])

    if 'Confidence' in props:
      self.__confidence = props['Confidence']

  @property
  def confidence(self)->float:
    return self.__confidence

  @property
  def bounding_box(self)->BoundingBox:
    return self.__bounding_box

class Label:
  def __init__(self, properties:dict)->None:
    self.__name = properties['Name']
    self.__confidence = properties['Confidence']
    self.__instances = [LabelInstance(x) for x in properties['Instances']]
    self.__parents = [ParentLabel(x) for x in properties['Parents']]

  @property
  def name(self)->str:
    return self.__name

  @property
  def confidence(self)->float:
    return self.__confidence

  @property
  def instances(self)->List[LabelInstance]:
    return self.__instances

  @property
  def parent_labels(self)->List[ParentLabel]:
    return self.__parents

class LabelDocument:
  def __init__(self, response:dict)->None:
    if 'Labels' not in response:
      raise ValueError('Invalid Document')

    self.__response = response
    self.__labels = [Label(x) for x in response['Labels']]

  def as_dict(self):
    return self.__response

  @property
  def labels(self)->List[Label]:
    return self.__labels

  @property
  def bounded_labels(self)->List[Label]:
    results = []
    for label in self.labels:
      for instance in label.instances:
        if instance.bounding_box != None:
          results.append(label)
          break

    return results
