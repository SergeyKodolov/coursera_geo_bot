import os
import psycopg2
from haversine import haversine, Unit


def create_connection():
    """Соединение с базой данных"""
    if os.getenv('DATABASE_URL'):
        url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(url, sslmode='require')
        print('ok')
    else:
        conn = psycopg2.connect(
            database="postgres",
            user="postgres",
            password="Ubupass",
            host="127.0.0.1",
            port="5432"
        )
    return conn


def check_tables(conn):
    """Создание таблиц, если нет"""
    try:
        with conn.cursor() as cur:
            with open('create_tables.sql') as sql:
                cur.execute(sql.read())
            conn.commit()
            print('ok')
    except Exception as ex:
        print(ex)


def create_user(conn, _id):
    """Добавление пользователя в базу данных"""
    with conn.cursor() as cur:
        sql = f'insert into users values ({_id}, 500)'
        try:
            cur.execute(sql)
        except Exception as ex:
            pass
        conn.commit()


def create_location(conn, user_id, title, address='null', location='null', photo='null'):
    """Создание местоположения"""
    with conn.cursor() as cur:
        sql = f"insert into locations (title, address, location, photo, user_id) " \
              f"values (" \
              f"'{title}', " \
              f"'{address or 'null'}', " \
              f"'{location  or 'null'}', " \
              f"'{photo  or 'null'}', " \
              f"'{user_id}') " \
              f"RETURNING location_id"
        try:
            cur.execute(sql)
        except Exception as ex:
            pass
        conn.commit()

        location_id = cur.fetchall()
        return int(location_id[0][0])


def get_location(conn, location_id):
    """Получить местоположение из базы"""
    with conn.cursor() as cur:
        sql = f"select title, address, location, photo from locations " \
              f"where location_id = {location_id}"
        try:
            cur.execute(sql)
        except Exception as ex:
            pass

        result = cur.fetchall()
        title, address, location, photo = result[0]
        return title, address, location, photo


def update_location(conn, loc_id, title=None, address=None, location=None, photo=None):
    """Обновить местоположение"""
    with conn.cursor() as cur:
        sql = ''
        sql += f'update locations set title = \'{title}\' where location_id = {loc_id};\n' if title else ''
        sql += f'update locations set address = \'{address}\' where location_id = {loc_id};\n' if address else ''
        sql += f'update locations set location = \'{location}\' where location_id = {loc_id};\n' if location else ''
        sql += f'update locations set photo = \'{photo}\' where location_id = {loc_id};\n' if photo else ''

        try:
            cur.execute(sql)
        except Exception as ex:
            pass

        conn.commit()


def are_there_locations(conn, user_id):
    """Проверка сохраненных местоположений"""
    with conn.cursor() as cur:
        sql = f'select count(*) from locations where user_id = {user_id}'

        try:
            cur.execute(sql)
        except Exception as ex:
            pass

        result = cur.fetchall()
        count = result[0][0]

    if count > 0:
        return True
    return False


def is_there_user(conn, user_id):
    """Проверка сохраненных местоположений"""
    with conn.cursor() as cur:
        sql = f'select count(*) from users where user_id = {user_id}'

        try:
            cur.execute(sql)
        except Exception as ex:
            pass

        result = cur.fetchall()
        count = result[0][0]

    if count == 1:
        return True
    return False


def delete_user_data(conn, user_id):
    """Удаление местоположений пользователя"""
    with conn.cursor() as cur:
        sql = f'delete from locations where user_id = {user_id};\n' \
              f'delete from users where user_id = {user_id};'
        try:
            cur.execute(sql)
        except Exception as ex:
            pass

        conn.commit()


def update_radius(conn, user_id, radius):
    """Установить радиус для пользователя"""
    with conn.cursor() as cur:
        sql = f'update users set radius = {radius} where user_id = {user_id}'

        cur.execute(sql)

        conn.commit()

def get_radius(conn, user_id):
    """Получить радиус пользователя"""
    with conn.cursor() as cur:
        sql = f'select radius from users where user_id = {user_id}'

        cur.execute(sql)

        result = cur.fetchall()
        radius = result[0][0]

        return radius


def get_locations_ids(conn, user_id):
    """Получить все местоположения пользователя"""
    with conn.cursor() as cur:
        sql = f'select location_id, location from locations where user_id = {user_id}'

        cur.execute(sql)

        result = cur.fetchall()
        locations_ids = [key for key, value in result]

        return locations_ids


def get_near_locations_ids(conn, user_location, locations_ids, radius):
    """Возвращает массив ближайших локаций"""
    near_locations_ids = []
    for location_id in locations_ids:
        title, address, location, photo = get_location(conn, location_id)
        if location:
            coord = (
                location['latitude'],
                location['longitude']
            )
            dist = haversine(coord, user_location, unit=Unit.METERS)
            if dist <= radius:
                near_locations_ids.append(location_id)

    return near_locations_ids
