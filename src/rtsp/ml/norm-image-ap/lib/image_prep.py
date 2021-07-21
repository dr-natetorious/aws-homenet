from typing import Tuple
from json import dumps, loads
from PIL import Image, ImageOps
from io import BytesIO

class ImagePrep:
  def __init__(self, buffer:bytes, size:Tuple[int,int]=(64,64)) -> None:
    self.__image = Image.frombytes(buffer)

    self.normalized  = self.original_image.resize(size, resample=Image.NEAREST)
    self.normalized = ImageOps.grayscale(self.normalized)
    
    output = BytesIO()
    self.normalized.save(output, format='PNG')
    self.response_body = output.getvalue()
    
  @property
  def original_image(self)-> Image:
    return self.__image
