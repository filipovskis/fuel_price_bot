import requests

from requests import Response
from bs4 import BeautifulSoup

class FuelStation():
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.data = None

    def set_unreliable(self, state):
        self.unreliable = state

    def get_data(self):
        return self.data
    
    def is_diesel(self, fuel_type):
        return fuel_type.lower().find('d') != -1
    
    def is_lpg(self, fuel_type):
        return fuel_type == 'Autogaze' or fuel_type == 'LPG'

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

class Virsi(FuelStation):
    def __init__(self):
        super().__init__("Virsi", "https://www.virsi.lv/en/private/fuel/fuel-price")
        self.set_unreliable(True) # prices differ among different stations, so we mark it as unreliable

    def scrape_data(self, response: Response) -> dict:
        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.find_all('p', class_='price')
        data = {}

        for div in divs:
            spans = div.find_all('span')
            name, price = spans[0].text.strip(), spans[1].text.strip()

            # no electricity prices, sorry
            if name.find('kW') != -1 or name == 'AdBLUE' or name == 'CNG':
                continue

            try:
                price_value = round(float(price), 2)
                data[name] = price_value
            except ValueError:
                print(f"Error converting price for {name}: {price}")


        return data

class Viada(FuelStation):
    image_references = {
        'petrol_95ecto_new': 'Petrol 95',
        # 'petrol_95ectoplus_new': 'Petrol 95+',
        'petrol_98_new': 'Petrol 98',
        'petrol_d_new': 'Diesel',
        # 'petrol_d_ecto_new': 'Diesel MultiX', # how this one could be cheaper than an ordinary one? I do not believe viada anymore
        'gaze': 'Autogaze',
    }

    def __init__(self):
        super().__init__("Viada", "https://www.viada.lv/zemakas-degvielas-cenas/")
        self.set_unreliable(True) # prices differ among different stations, so we mark it as unreliable

    def scrape_data(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')[1:] # first one is header
        data = {}
    
        for row in rows:
            tds = row.find_all('td')
            if len(tds) > 0:
                imgHolder = tds[0].find('img')
                if imgHolder is not None:
                    try:
                        imgID = imgHolder['src'].split('/')[-1].split('.')[0].lower()
                    except Exception as e:
                        print(f"Error extracting image ID: {e}")
                        continue

                    name = self.image_references.get(imgID)
                    if name is not None:
                        price = tds[1].text.strip().split()[0]
                        try:
                            price_value = round(float(price), 2)
                            data[name] = price_value
                        except ValueError:
                            print(f"Error converting price for {name}: {price}")

        return data
    
def get_station_by_name(name):
    stations = [Circle_K(), Neste(), Virsi(), Viada()]
    for station in stations:
        if station.name == name:
            return station
    return None