import os
from typing import Dict

from dadata import Dadata
from db import db

DADATA_TOKEN = os.getenv('DADATA_TOKEN')
dadata = Dadata(DADATA_TOKEN)


def clean_text(text: str) -> db.Location:
    """Возвращает местоположение по введенному тексту"""
    location = db.Location(title=text)

    result = dadata.suggest('address', text)
    if len(result) > 0:
        result = result[0]
        if result is not None:
            location.address = result['value']
            if result['data']['geo_lat'] is not None \
                    and result['data']['geo_lon'] is not None:
                location.location = {
                    'latitude': float(result['data']['geo_lat']),
                    'longitude': float(result['data']['geo_lon'])
                }

    return location


def clean_geolocate(message_location: Dict) -> db.Location:
    """Возвращает адрес и локацию по координатам"""
    geo_lat, geo_lon = message_location["latitude"], message_location["longitude"]
    result = dadata.geolocate(name='address', lat=geo_lat, lon=geo_lon)

    location = db.Location()

    if len(result) > 0:
        location.address = result[0]['value']
    else:
        location.address = f'{message_location["latitude"]}, ' \
                  f'{message_location["longitude"]}'
    location.location = message_location

    return location
