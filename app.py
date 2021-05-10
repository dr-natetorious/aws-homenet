#!/usr/bin/env python3
import os.path
from typing import List
from aws_cdk import core
from infra.interfaces  import ILandingZone
from infra.basenet import Chatham, Hybrid
src_root_dir = os.path.join(os.path.dirname(__file__))

us_east_1 = core.Environment(region="us-east-1", account='581361757134')

class NetworkingApp(core.App):
  def __init__(self, **kwargs) ->None:
    super().__init__(**kwargs)

    # Main setup
    self.hybrid = Hybrid(self,'HomeNet-Hybrid', env=us_east_1)
    self.chatham = Chatham(self,'HomeNet-Chatham', vpc=self.hybrid.vpc, env=us_east_1)

  @property
  def zones(self)->List[ILandingZone]:
    return [ self.virginia, self.chatham ]

app = NetworkingApp()
app.synth()
