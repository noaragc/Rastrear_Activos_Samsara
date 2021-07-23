import configparser
import asyncio
#Librería para Envío de Correos Electrónicos
import smtplib
#
from datetime import datetime
from dateutil import tz

from email.message import EmailMessage

from aiohttp import ClientSession

from_zone = tz.tzutc()
to_zone = tz.tzlocal()

async def main():
    api_key = get_api_key()
    base_url = get_base_url()
    url_for_vehicles = get_url_for_vehicles()
    url_for_location_v = get_url_for_location_v()
    url_for_gmaps = get_gmaps_base_url()

    while True:
        context = []
        #await asyncio.sleep(n)
        async with ClientSession() as session:
            vehicles = await get_vehicles(session, base_url+url_for_vehicles, api_key)
        
        vehicles_new = {}
        vehicles_location = {}
        async with ClientSession() as session:
            for vehicle in vehicles:
                if 'tags' in vehicle:
                    for x in vehicle['tags']:
                        if x['name'].find('Valija') == -1:
                            continue
                        else:
                            task = await get_location_for_vehicle(session, base_url + url_for_location_v + vehicle['id'], api_key) #obtener la ubicación de los tractos
                            vehicles_location[vehicle['id']] = task['data'] #agregar las ubicaciones de los tractos que tienen asignada la valija a un nuevo diccionario
                            vehicles_new[vehicle['id']] = vehicle #agregar vehículos que si tienen asignada la valija al nuevo diccionario
        
        for key, value in vehicles_location.items():
            for v in value:
                if 'locations' in v:
                    for x in v['locations']:
                        if 'reverseGeo' in x:
                            for kV, vV in vehicles_new.items():
                                if vV['id'] == v['id']:
                                    for vv in vV['tags']:
                                        url_gmap = url_for_gmaps + str(x['latitude'])+','+str(x['longitude'])+'/@'+str(x['latitude'])+','+str(x['longitude'])+',14z/data=!4m2!4m1!3e0'
                                        location_data = v['id'], v['name'], vV['notes'], x['reverseGeo']['formattedLocation'],x['time'], x['latitude'], x['longitude'], vv['name'], url_gmap
                                        context.append(location_data)
                                        #print()
                            
                            #Enviar Whatsapp
                            #py.sendwhatmsg(f'+526141627692','Tractor: {0} - Ubicación: {1} - Tiempo y Hora UTC: {2} - GoogleMaps: {3}'.format(v['name'], x['reverseGeo']['formattedLocation'],
                            #x['time'], url_gmap), 13, 2)   
        #print(context)
        for x in context:
            send_email(x)
#https://maps.google.com/maps/?q=&layer=c&cbll=18.85737859,-98.93522693
#https://www.google.com.mx/maps/dir//18.86009089,-98.933726539/@18.86009089,-98.933726539,14z/data=!4m2!4m1!3e0

async def get_vehicles(session, url, api_key):
    async with session.get(url, headers={'Authorization': 'Bearer {0}'.format(api_key), 'Content-Type':'application/json; charset=utf-8'}) as response:
        res = await response.json()
        return res['data']

async def get_location_for_vehicle(session, url, api_key):
    async with session.get(url, headers={'Authorization': 'Bearer {0}'.format(api_key), 'Content-Type':'application/json; charset=utf-8'}) as response:
        res = await response.json()
        return res

def get_url_for_vehicles():
    config = get_config_file()
    return config['samsara_url_vehicles']['url_for_vehicles']

def get_url_for_location_v():
    config = get_config_file()
    return config['samsara_url_location_v']['url_for_loc_v']

def get_base_url():
    config = get_config_file()
    return config['samsara_base_url']['base_url']

def get_gmaps_base_url():
    config = get_config_file()
    return config['google_url_maps']['base_url']

def get_api_key():
    config = get_config_file()
    return config['samsara_api_key']['api_key']

def get_config_file():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

def get_config_email():
    config = get_config_file()
    return config

def convert_time_zone(utc_time):
    utcTime = datetime.strptime(utc_time, '%Y-%m-%dT%H:%M:%S%z')
    utcTime = utcTime.replace(tzinfo=from_zone)
    local_time = utcTime.astimezone(to_zone)
    return local_time.strftime('%d-%m-%Y %H:%M:%S')

def send_email(context):
    config = get_config_email()
    local_time = convert_time_zone(context[4])

    print(f'Id: {context[0]} - Tractor: {context[1]} -> {context[7]}\nAnotaciones: {context[2]}\nUbicación: {context[3]}\nLatitude: {context[5]} - Longitude: {context[6]}\n{context[8]}')
    
    sender_email_address = config['email_config']['sender_email_address']
    sender_email_pwd = config['email_config']['sender_email_pwd']
    email_smtp = config['email_config']['email_smtp']
    email_port = config['email_config']['email_server_port']

    email_subject = f'NOTIFICACIÓN | {context[7]} Tracto '+ context[1]
    receiver_email_address = ['noelaguirre@trasoto.com','valija@trasoto.com']

    try:
        message = EmailMessage()

        message_html = f'''
<!DOCTYPE html> 
<head> 
</head>    
    <body>        
        <h1>Estado de la {context[7]}</h1>        
        <p>Tractor: <strong>{context[1]}</strong></p>
        <p>Anotaciones:<br><strong>{context[2]}</strong></p>
        <p>Ubicación Actual: <strong>{context[3]}</strong></p>
        <p>Tiempo y Hora: <strong>{local_time}</strong></p>  
        <a href="{context[8]}">Ver en Google Maps</a>
    </body> 
</html>
        '''

        message['Subject'] = email_subject
        message['From'] = sender_email_address
        message['To'] = receiver_email_address

        message.set_content(message_html, subtype='html')

        server = smtplib.SMTP_SSL(email_smtp+':'+email_port)

        server.login(sender_email_address, sender_email_pwd)

        server.send_message(message)

        print('Email Enviado')
    except Exception as err:
        print('Error al enviar el correo: {0}'.format(err))
    finally:
        server.quit()
    print()
    
if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print('Cerrando Bucle')
        loop.close()