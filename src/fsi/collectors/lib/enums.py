from enum import Enum

class RunStatus(Enum):
  MORE_AVAILABLE='MORE_AVAILABLE'
  COMPLETE='COMPLETE'

class SecurityStatus(Enum):
  NORMAL='NORMAL'
  UNKNOWN='UNKOWN'
  CLOSED='CLOSED'
  NONE='NONE'
  HALTED='HALTED'
  DELETED='DELETED'

  @staticmethod
  def standard_ignore_list()->list:
    return [
      SecurityStatus.UNKNOWN,
      SecurityStatus.NONE,
      SecurityStatus.CLOSED,
      SecurityStatus.DELETED
    ]
