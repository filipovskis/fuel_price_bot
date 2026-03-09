import requests

from requests import Response
from bs4 import BeautifulSoup

class FuelStation():
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.data = None

    def get_data(self):
        return self.data
    
    def is_diesel(self, fuel_type):
        return fuel_type.lower().find('d') != -1
    
    def is_lpg(self, fuel_type):
        return fuel_type == 'Autogaze'

    def collect_data(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                data = self.scrape_data(response)
                if data:
                    print(f"Successfully collected data for {self.name}: {data}")
                    self.data = data
                    return data
                else:
                    print(f"No data found for {self.name}.")
        except Exception as e:
            print(f"Error during HTTP request for {self.name}: {e}")

    def scrape_data(self, response: Response) -> dict:
        return {}

class Neste(FuelStation):
    def __init__(self):
        super().__init__("Neste", "https://www.neste.lv/lv/content/degvielas-cenas")

    def scrape_data(self, response: Response) -> dict:
        soup = BeautifulSoup(response.text, 'html.parser') 
        divPrices = soup.find_all('div', class_='field__item even')
        spanElements = divPrices[0].find_all('span')
        
        lastName = None
        data = {}
    
        for span in spanElements:
            text = span.text.strip()
        
            try:
                val = round(float(text), 2)
            except ValueError:
                lastName = text
                continue

            data[lastName.replace('Neste', '')] = val

        return data

class Circle_K(FuelStation):
    diesel_types = ['Dmiles', 'Dmiles+', 'miles+ XTL']

    def __init__(self):
        super().__init__("Circle K", "https://circlek.lv/degviela-miles/degvielas-cenas")

    def is_diesel(self, fuel_type):
        return fuel_type in self.diesel_types

    def scrape_data(self, response: Response) -> dict:
        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.find_all('tr')
        
        data = {}
        for tr in elements:
            tds = tr.find_all('td')
            if len(tds) >= 2:
                fuel_type = tds[0].text.strip()
                price = tds[1].text.strip().split()[0]

                try:
                    price_value = round(float(price), 2)
                    data[fuel_type] = price_value
                except ValueError:
                    print(f"Error converting price for {fuel_type}: {price}")
                    return {}
        
        return data
    
def get_station_by_name(name):
    stations = [Circle_K(), Neste()]
    for station in stations:
        if station.name == name:
            return station
    return None