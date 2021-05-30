from typing import List, Tuple


class BoundingBox:
  def __init__(self, props:dict)->None:
    self.__width = float(props['width']) if 'width' in props else 0
    self.__height = float(props['height']) if 'height' in props else 0
    self.__left = float(props['left']) if 'left' in props else 0
    self.__top = float(props['top']) if 'top' in props else 0
    self.__props = props

  def as_dict(self)->dict:
    return self.__props

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

  @property
  def shape(self)->List[Tuple[float,float]]:
    return [
      (self.left,self.top),
      (self.left +self.width, self.top+self.height)
    ]

  @property
  def is_usable(self)->bool:
    return self.width > 0 and self.height >0 and self.top >0 and self.left >0