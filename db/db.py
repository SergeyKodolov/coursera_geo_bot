import json
import os
from dataclasses import dataclass
from typing import List

import psycopg2
from haversine import haversine, Unit

import sqlite3


@dataclass
class Location:
    """Структура геопозиции"""
    title: str = "Геопозиция"
    address: str = None
    location: dict = None
    photo: dict = None

    def get_str_address(self):
        if self.address:
            return self.address
        else:
            return 'null'

    def get_str_location(self):
        if self.location:
            if type(self.location) is dict:
                return json.dumps(self.location)
            else:
                return self.location
        else:
            return 'null'

    def get_str_photo(self):
        if self.photo:
            if type(self.photo) is dict:
                return json.dumps(self.photo)
            else:
                return self.photo
        else:
            return 'null'


# Соединение с базой данных
if os.getenv('DATABASE_URL'):
    url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(url, sslmode='require')
else:
    conn = sqlite3.connect(os.path.join("db", "locations.db"), check_same_thread=False)
print('db connection: ok')
cursor = conn.cursor()


def create_user(_id: int):
    """Добавление пользователя в базу данных"""
    sql = f'INSERT INTO users VALUES ({_id}, 500)'
    try:
        cursor.execute(sql)
        conn.commit()
    except Exception as ex:
        print(ex)


def create_location(user_id: int, location: Location) -> int:
    """Создание местоположения"""
    if type(cursor) is sqlite3.Cursor:
        loc_id = create_location_sqlite(user_id, location)
    else:
        loc_id = create_location_postgres(user_id, location)
    return loc_id


def create_location_sqlite(user_id: int, location: Location) -> int:
    """Создание местоположения"""
    sql = f"INSERT INTO locations (title, address, location, photo, user_id) " \
          f"VALUES (" \
          f"'{location.title}', " \
          f"'{location.get_str_address()}', " \
          f"'{location.get_str_location()}', " \
          f"'{location.get_str_photo()}', " \
          f"'{user_id}') "
    try:
        cursor.execute(sql)
    except Exception as ex:
        print(ex)
        return -1

    location_id = cursor.lastrowid
    conn.commit()

    return location_id


def create_location_postgres(user_id: int, location: Location) -> int:
    """Создание местоположения"""
    sql = f"INSERT INTO locations (title, address, location, photo, user_id) " \
          f"VALUES (" \
          f"'{location.title}', " \
          f"'{location.get_str_address()}', " \
          f"'{location.get_str_location()}', " \
          f"'{location.get_str_photo()}', " \
          f"'{user_id}') " \
          f"RETURNING location_id"
    try:
        cursor.execute(sql)
    except Exception as ex:
        print(ex)
        return -1

    conn.commit()

    location_id = cursor.fetchall()
    return int(location_id[0][0])


def get_location(location_id: int) -> Location:
    """Получить местоположение из базы"""
    sql = f"SELECT title, address, location, photo FROM locations " \
          f"WHERE location_id = {location_id}"
    try:
        cursor.execute(sql)
    except Exception as ex:
        print(ex)

    result = cursor.fetchall()
    title, address, location, photo = [None if item == 'null' else item for item in result[0]]
    if location:
        location = json.loads(location)
    if photo:
        photo = json.loads(photo)

    return Location(title, address, location, photo)


def update_location(loc_id: int, location: Location):
    """Обновить местоположение"""
    sql = ''
    sql += f'UPDATE locations SET title = \'{location.title}\' ' \
           f'WHERE location_id = {loc_id};\n'

    sql += f'UPDATE locations SET address = \'{location.get_str_address()}\' ' \
           f'WHERE location_id = {loc_id};\n' if location.address else ''

    sql += f'UPDATE locations SET location = \'{location.get_str_location()}\' ' \
           f'WHERE location_id = {loc_id};\n' if location.location else ''

    sql += f'UPDATE locations SET photo = \'{location.get_str_photo()}\' ' \
           f'WHERE location_id = {loc_id};\n' if location.photo else ''

    try:
        if type(cursor) is sqlite3.Cursor:
            cursor.executescript(sql)
        else:
            cursor.execute(sql)
    except Exception as ex:
        print(ex)

    conn.commit()


def are_there_locations(user_id: int) -> bool:
    """Проверка сохраненных местоположений"""
    sql = f'SELECT COUNT(*) FROM locations WHERE user_id = {user_id}'
    try:
        cursor.execute(sql)
    except Exception as ex:
        print(ex)

    result = cursor.fetchall()
    count = result[0][0]

    if count > 0:
        return True
    return False


def is_there_user(user_id: int) -> bool:
    """Проверка существования пользователя"""
    sql = f'SELECT COUNT(*) FROM users WHERE user_id = {user_id}'
    cursor.execute(sql)
    result = cursor.fetchall()
    count = result[0][0]

    if count == 1:
        return True
    return False


def delete_user_data(user_id: int):
    """Удаление местоположений пользователя"""
    sql = f'DELETE FROM locations WHERE user_id = {user_id};\n' \
          f'DELETE FROM users WHERE user_id = {user_id};'
    try:
        cursor.execute(sql)
        conn.commit()
    except Exception as ex:
        print(ex)


def update_radius(user_id: int, radius: float):
    """Установить радиус для пользователя"""
    sql = f'UPDATE users SET radius = {radius} WHERE user_id = {user_id}'
    cursor.execute(sql)
    conn.commit()


def get_radius(user_id: int) -> float:
    """Получить радиус пользователя"""
    sql = f'SELECT radius FROM users WHERE user_id = {user_id}'
    cursor.execute(sql)
    result = cursor.fetchall()
    radius = result[0][0]
    return radius


def get_locations_ids(user_id: int) -> List[int]:
    """Получить все местоположения пользователя"""
    sql = f'SELECT location_id, location FROM locations WHERE user_id = {user_id}'
    cursor.execute(sql)
    result = cursor.fetchall()
    locations_ids = [key for key, value in result]
    return locations_ids


def get_near_locations_ids(user_location: int, locations_ids: List[int], radius: float) -> List[int]:
    """Возвращает массив ближайших локаций"""
    near_locations_ids = []
    for location_id in locations_ids:
        title, address, location, photo = get_location(location_id)
        if location:
            coord = (
                location['latitude'],
                location['longitude']
            )
            dist = haversine(coord, user_location, unit=Unit.METERS)
            if dist <= radius:
                near_locations_ids.append(location_id)

    return near_locations_ids


def _init_db():
    """Инициализация БД"""
    try:
        with open('db/createdb.sql') as file:
            sql = file.read()
            if type(cursor) is sqlite3.Cursor:
                sql = sql.format(type='INTEGER', autoincrement='autoincrement')
                cursor.executescript(sql)
            else:
                sql = sql.format(type='serial', autoincrement='')
                cursor.execute(sql)
        conn.commit()
        print('create tables: ok')
    except Exception as ex:
        print(ex)


def check_tables_exist():
    """Проверка существования БД"""
    if os.getenv('DATABASE_URL'):
        sql = "SELECT Table_name FROM information_schema.tables " \
              "WHERE Table_name IN ('users', 'locations')"
    else:
        sql = "SELECT name FROM sqlite_master " \
              "WHERE type='table' AND name IN ('users', 'locations')"

        cursor.execute(sql)
        table_exists = cursor.fetchall()
        if len(table_exists) == 2:
            return
        _init_db()


check_tables_exist()
