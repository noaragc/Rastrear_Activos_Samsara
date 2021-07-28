import os
#import configparser
import asyncio
#Librería para Envío de Correos Electrónicos
import smtplib
import pytz

from datetime import datetime
from email.message import EmailMessage
from aiohttp import ClientSession

tz = pytz.timezone('America/Chihuahua')

async def main():
    #api_key = get_api_key()
    api_key = os.environ['SM_API_KEY']
    #base_url = get_base_url()
    base_url = os.environ['SM_BASE_URL']
    #url_for_vehicles = get_url_for_vehicles()
    url_for_vehicles = os.environ['SM_URL_FOR_VEHICLES']
    #url_for_location_v = get_url_for_location_v()
    url_for_location_v = os.environ['SM_URL_FOR_LOCATIONS']
    #url_for_gmaps = get_gmaps_base_url()
    url_for_gmaps = os.environ['GM_BASE_URL']
    #url_for_assets = get_url_for_assets()
    url_for_assets = os.environ['SM_URL_FOR_ASSETS']

    context = []
    async with ClientSession() as session:
        vehicles = await get_vehicles(session, base_url+url_for_vehicles, api_key)
        assets = await get_assets(session, base_url+url_for_assets, api_key)
    
    vehicles_new = {}
    vehicles_location = {}
    assets_new = {}
    async with ClientSession() as session:
        for vehicle in vehicles:
            if 'tags' in vehicle:
                for x in vehicle['tags']:
                    if x['name'].find('Kalish') == -1:
                        continue
                    else:
                        task = await get_location_for_vehicle(session, base_url + url_for_location_v + vehicle['id'], api_key) #obtener la ubicación de los tractos
                        vehicles_location[vehicle['id']] = task['data'] #agregar las ubicaciones de los tractos que tienen asignada la valija a un nuevo diccionario
                        vehicles_new[vehicle['id']] = vehicle #agregar vehículos que si tienen asignada la valija al nuevo diccionario
    
    #print()
    for asset in assets:
        if 'vehicleId' in asset:
            for k, v in vehicles_new.items():
                if int(v['id']) == int(asset['vehicleId']):
                    print('Vehicle {0} - Asset {1}'.format(v['id'], asset['vehicleId']))
                    assets_new[v['id']] = asset

    #print()
    #[print(x) for v,x in vehicles_new.items()]
    print(assets_new)
    for key, value in vehicles_location.items():
        for v in value:
            if 'locations' in v:
                for x in v['locations']:
                    if 'reverseGeo' in x:
                        for kV, vV in vehicles_new.items():
                            if vV['id'] == v['id']:
                                if assets_new:
                                    for kA, asset in assets_new.items():
                                        if int(asset['vehicleId']) == int(v['id']):
                                            for vv in vV['tags']:
                                                url_gmap = url_for_gmaps + str(x['latitude'])+','+str(x['longitude'])
                                                location_data = v['id'], v['name'], vV['notes'], x['reverseGeo']['formattedLocation'],x['time'], x['latitude'], x['longitude'], vv['name'], url_gmap, asset['name']
                                                context.append(location_data)
                                        else:
                                            for vv in vV['tags']:
                                                url_gmap = url_for_gmaps + str(x['latitude'])+','+str(x['longitude'])
                                                location_data = v['id'], v['name'], vV['notes'], x['reverseGeo']['formattedLocation'],x['time'], x['latitude'], x['longitude'], vv['name'], url_gmap
                                                context.append(location_data)
                                elif not assets_new:
                                    for vv in vV['tags']:
                                        url_gmap = url_for_gmaps + str(x['latitude'])+','+str(x['longitude'])
                                        location_data = v['id'], v['name'], vV['notes'], x['reverseGeo']['formattedLocation'],x['time'], x['latitude'], x['longitude'], vv['name'], url_gmap
                                        context.append(location_data)
    #print()
    #[print(con) for con in context]
    if not context:
        print('Sin viajes de Kalish')
    else:
        for x in context:
            if x[7].find('Kalish') == -1:
                continue
            else:
                send_email(x)

async def get_vehicles(session, url, api_key):
    async with session.get(url, headers={'Authorization': 'Bearer {0}'.format(api_key), 'Content-Type':'application/json; charset=utf-8'}) as response:
        res = await response.json()
        return res['data']

async def get_assets(session, url, api_key):
    async with session.get(url, headers={'Authorization': 'Bearer {0}'.format(api_key), 'Content-Type':'application/json; charset=utf-8'}) as response:
        res = await response.json()
        return res['assets']

async def get_location_for_vehicle(session, url, api_key):
    async with session.get(url, headers={'Authorization': 'Bearer {0}'.format(api_key), 'Content-Type':'application/json; charset=utf-8'}) as response:
        res = await response.json()
        return res

# def get_url_for_assets():
#     config = get_config_file()
#     return config['samsara_url_vehicles']['url_for_assets']

# def get_url_for_vehicles():
#    config = get_config_file()
#    return config['samsara_url_vehicles']['url_for_vehicles']

# def get_url_for_location_v():
#    config = get_config_file()
#    return config['samsara_url_location_v']['url_for_loc_v']

# def get_base_url():
#    config = get_config_file()
#    return config['samsara_base_url']['base_url']

# def get_gmaps_base_url():
#    config = get_config_file()
#    return config['google_url_maps']['base_url']

# def get_api_key():
#    config = get_config_file()
#    return config['samsara_api_key']['api_key']

# def get_config_file():
#    config = configparser.ConfigParser()
#    config.read('config.ini')
#    return config

# def get_config_email():
#    config = get_config_file()
#    return config

def convert_time_zone(utc_time):
    utcTime = datetime.strptime(utc_time, '%Y-%m-%dT%H:%M:%S%z')
    new_ct = utcTime.astimezone(tz)
    local_time = new_ct.strftime('%d-%m-%Y %H:%M:%S')
    return local_time

def send_email(context):
    #config = get_config_email()
    local_time = convert_time_zone(context[4])
    
    if len(context) == 9:
        trailer = 'No Asignada'
    else:
        trailer = context[9]
    
    print(f'{local_time}\nId: {context[0]} - Tractor: {context[1]} -> en Caja: {trailer}\nUbicación: {context[3]}\nLatitude: {context[5]} - Longitude: {context[6]}\n{context[8]}\n{context[2]}')
    
    #sender_email_address = config['email_config']['sender_email_address']
    sender_email_address = os.environ['sender_email_address']
    #sender_email_pwd = config['email_config']['sender_email_pwd']
    sender_email_pwd = os.environ['sender_email_pwd']
    #email_smtp = config['email_config']['email_smtp']
    email_smtp = os.environ['email_smtp']
    #email_port = config['email_config']['email_server_port']
    email_port = os.environ['email_server_port']

    email_subject = f'NOTIFICACIÓN | {context[7]} Tracto {context[1]} - Caja {trailer}'
    
    #Get the emails that will receive the emails
    list_of_emails = os.environ['receiver_dir_email_address']
    #Emails must be separated by comma
    list_separated = list_of_emails.split(',')

    try:
        message = EmailMessage()

        if context[2] == '':
            message_html = f'''
<!DOCTYPE html> 
<head> 
</head>    
    <body>        
        <h1>Estado del Viaje: {context[7]}</h1>        
        <p>Tractor: <strong>{context[1]}</strong></p>
        <p>En Caja:<br><strong>{trailer}</strong></p>
        <p>Ubicación Actual: <strong>{context[3]}</strong></p>
        <p>Fecha y Hora: <strong>{local_time}</strong></p>
        <p><strong>No se Generó Liga para Rastrear en Samsara</strong></p>
        <p><a href="{context[8]}">Ver en Google Maps</a></p>
    </body> 
</html>
        '''
        else:
            message_html = f'''
<!DOCTYPE html> 
<head> 
</head>    
    <body>        
        <h1>Estado del Viaje: {context[7]}</h1>        
        <p>Tractor: <strong>{context[1]}</strong></p>
        <p>En Caja:<br><strong>{trailer}</strong></p>
        <p>Ubicación Actual: <strong>{context[3]}</strong></p>
        <p>Fecha y Hora: <strong>{local_time}</strong></p>
        <p><a href="{context[2]}">Rastrear en Samsara</a></p>
        <p><a href="{context[8]}">Ver en Google Maps</a></p>
    </body> 
</html>
        '''

        message['Subject'] = email_subject
        message['From'] = sender_email_address
        message['To'] = list_separated
        #message['To'] = ['prueba@prueba.com']

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
        #loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print('Loop ended')
        loop.close()