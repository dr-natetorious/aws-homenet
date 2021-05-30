import requests
import calendar
import typing
from models import EarningReport
from datetime import datetime
from bs4 import BeautifulSoup

class RttNewsEarningsClient:

  def __init__(self, base_url:str='https://www.rttnews.com/Calendar/Earnings.aspx'):
    """
    Create a new instance
    """
    self.__base_url = base_url

  def get_for_date(self, date:datetime=None, date_str:str=None) -> typing.List[EarningReport]:
    """
    Gets the information for a given date.
    """
    if date is None:
      if date_str is None:
        raise AssertionError("Neither date or data_str are set")
      else:
        date = datetime.strptime(date_str,"%Y-%m-%d")
    
    url = self.__get_url_for_date(date)
    data_table = self.__parse_url(url)
    return data_table

  def __parse_url(self, url) -> typing.List[EarningReport]:
    """
    Fetches and parses the requested url.
    """
    html = requests.get(url)
    soup = BeautifulSoup(html.text,'lxml')
    symbols=[]
    for cell in soup.find_all('div', attrs={'data-th':'Symbol'}):
        symbols.append(cell.find('a').text)

    periods=[]
    for cell in soup.find_all('div', attrs={'data-th':'Period'}):
      periods.append(cell.text)
        
    est=[]
    for cell in soup.find_all('div', attrs={'data-th':'Estimated EPS'}):
      est.append(cell.text)

    previous=[]
    for cell in soup.find_all('div', attrs={'data-th':'Year Ago EPS'}):
      previous.append(cell.text)
        
    actual=[]
    for cell in soup.find_all('div', attrs={'data-th':'Actual EPS'}):
      actual.append(cell.text)
        
    time=[]
    for cell in soup.find_all('div', attrs={'data-th':'Time'}):
      time.append(cell.text)

    data_table = []
    for ix in range(0,len(symbols)):
      data_table.append(EarningReport(
        symbol= symbols[ix],
        period= periods[ix],
        eps_est= RttNewsEarningsClient.__clean_price(est[ix]),
        eps_last_year= RttNewsEarningsClient.__clean_price(previous[ix]),
        eps_actual= RttNewsEarningsClient.__clean_price(actual[ix]),
        time= time[ix]
      ))

    return data_table

  def __get_url_for_date(self,dt:datetime) -> str:
    """
    Website expects the query in format "DD-Month-Year"
    """
    date_str = "{d}-{m}-{y}".format(d=dt.day,m=calendar.month_abbr[dt.month], y=dt.year)
    return "{base}?Date={date_str}".format(
      base=self.__base_url,
      date_str=date_str)
  
  @staticmethod
  def __clean_price(value:str):
    return value.replace('$','').replace(' ','')
