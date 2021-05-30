class EarningReport:

  def __init__(self, symbol:str, period:str, eps_est:str, eps_last_year:str, eps_actual:str, time:str)-> None:
    self.symbol = symbol
    self.period = period
    self.eps_est = eps_est
    self.eps_last_year = eps_last_year
    self.eps_actual = eps_actual
    self.time = time

  def to_hash(self)-> dict:
    return {
      'symbol': self.symbol,
      'period': self.period,
      'eps_est': self.eps_est,
      'eps_last_year': self.eps_last_year,
      'eps_actual': self.eps_actual,
      'time': self.time
    }
  
  @staticmethod
  def from_hash(hash:dict):
    return EarningReport(
      symbol= hash['symbol'],
      period= hash['period'],
      eps_est= hash['eps_est'],
      eps_last_year= hash['eps_last_year'],
      eps_actual= hash['eps_actual'],
      time= hash['time'])
