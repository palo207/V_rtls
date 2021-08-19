"""
Created on Wed Jun 10 13:37:29 2020

@author: PAVA
"""
import json
import socket
import pyodbc
from datetime import timezone
from datetime import datetime
import time
import websocket
from config import (destUri,
                    X_API_KEY,
                    driver, 
                    database,
                    uid,
                    password,
                    server)
import pandas as pd

def check_if_exit(zone_name):
    return zone_name.startswith('X')


def get_outside_loc(old_zone_name,zone_name):
    if zone_name == 'X1':
        return 7.38,20.34
    elif zone_name == 'X2':
        return 10.41,46.30
    elif zone_name == 'X3':
        return 19.25,46.30
    elif zone_name == 'X4':
        return 28.16,46.30
    elif zone_name == 'X5':
        return 40.51,46.30
    elif zone_name == 'X6':
        return 55.51,46.30
    elif zone_name == 'X7':
        return 93.23,46.30
    elif zone_name == 'X8':
        return 119.5,46.30
    elif zone_name == 'X9':
        return 119.5,13.38

data=pd.read_excel("rtls_tag_names.xlsx", header=None)
tag_ids = list(data.iloc[:,1])
mac_addr = list(data.iloc[:,9])
dict_of_tags = {}
for id in range(0,len(tag_ids),1):
    dict_of_tags[mac_addr[id]]=tag_ids[id]
    
cnxn = pyodbc.connect(driver="{}".format(driver),
                      server=server, 
                      database=database,               
                      uid=uid,
		              password=password)

def write_data_db(message,cnxn=cnxn):
    parse=json.loads(message)
    try:
        tag_id = dict_of_tags[str(parse["body"]["address"])]
    except:
        tag_id = ('rtls_tag_' + str(parse["body"]["address"])[2:]).upper()
    address = str(parse["body"]["address"])
    posx = str(parse["body"]["datastreams"][0]["current_value"])
    posy = str(parse["body"]["datastreams"][1]["current_value"])
    float_posx = float(posx) 
    float_posy= float(posy)
    
    if "zones" in parse["body"]:
        zone_id = str(parse["body"]["zones"][0]["id"])
        zone_type = str(parse["body"]["zones"][0]["type"])
        zone_name = str(parse["body"]["zones"][0]["name"])
        if len(zone_name)>2:
            zone_name = zone_name[0:2]
    
    else:
        zone_id = "0"
        zone_type = "0"
        zone_name = "0"

    zone_enter = datetime.now().replace(microsecond=0)
    cursor = cnxn.cursor()
    SQLCommand = ("SELECT TOP 1 zone_name from {}.sap.rtls_tags WHERE tag_id = ?".format(database))
    Values = [tag_id]
    try:
        cursor.execute(SQLCommand, Values)
        result = cursor.fetchall()
    except Exception as e:
        log = open('log.txt','a')
        log_date = datetime.now()
        log.write("{} {} {}".format(e,log_date,SQLCommand))
    
    
    if result:
        old_zone_name  = str(result[0][0])
        if (old_zone_name == zone_name) or (zone_name == "0"):
            SQLCommand = ("UPDATE {}.sap.rtls_tags SET address = ?, PosX =?, PosY = ?, zone_id = ?, zone_type = ?, zone_name = ? WHERE tag_id = ?".format(database))
            Values = [address, posx, posy, zone_id, zone_type, old_zone_name, tag_id]
            try:
                cursor.execute(SQLCommand, Values)
                cnxn.commit()
            except Exception as e:
                log = open('log.txt','a')
                log_date = datetime.now()
                log.write("{} {} {}".format(e,log_date,SQLCommand))

        else:
            if check_if_exit(zone_name):
                try:
                    posx,posy = get_outside_loc(old_zone_name,zone_name)
                except:
                    pass

            SQLCommand = ("UPDATE {}.sap.rtls_tags SET address = ?, PosX =?, PosY = ?, zone_id = ?, zone_type = ?, zone_name = ?, zone_enter = ?  WHERE tag_id = ?".format(database))
            Values = [address, posx, posy, zone_id, zone_type, zone_name, zone_enter, tag_id]
            try:
                cursor.execute(SQLCommand, Values)
                cnxn.commit()
            except Exception as e:
                log = open('log.txt','a')
                log_date = datetime.now()
                log.write("{} {} {}".format(e,log_date,SQLCommand))

        SQLCommand = ("UPDATE {}.sap.tag_location x=?,y=? WHERE tag_id = ?".format(database))
        Values = [float_posx, float_posy,tag_id]
        try:
            cursor.execute(SQLCommand, Values)
            cnxn.commit()
        except Exception as e:
            log = open('log.txt','a')
            log_date = datetime.now()
            log.write("{} {} {}".format(e,log_date,SQLCommand))

    else:
        print('inserting new tag into db')
        SQLCommand = ("INSERT INTO {}.sap.rtls_tags(tag_id, address, PosX, PosY, zone_id, zone_type, zone_name, zone_enter, paired, paired_id) VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(database))
        Values = [tag_id, address, posx, posy, zone_id, zone_type, zone_name, zone_enter, 0, '-' ]
        print(Values)
        try:
            cursor.execute(SQLCommand, Values)
            cnxn.commit()
        except Exception as e:
            log = open('log.txt','a')
            log_date = datetime.now()
            log.write("{} {} {}".format(e,log_date,SQLCommand))

        SQLCommand = ("INSERT INTO {}.sap.tag_location(tag_id,x,y) VALUES(?, ?, ?)".format(database))
        Values = [tag_id,  float_posx, float_posy]
        try:
            cursor.execute(SQLCommand, Values)
            cnxn.commit()
        except Exception as e:
            log = open('log.txt','a')
            log_date = datetime.now()
            log.write("{} {} {}".format(e,log_date,SQLCommand))

def on_message(ws, message):
    print(message)
    try:
        write_data_db(message=message)
    except Exception as e:
        log = open('log.txt','a')
        log_date = datetime.now()
        log.write("{} {} {}".format(e,log_date,message))
    
def on_error(ws, error):
    print (error)
def on_close(ws):
    print ("### closed ###")
def on_open(ws):
    print ("### opened ###")
    msg = "{\"headers\":{\"X-ApiKey\":\""+ X_API_KEY +"\"},\"method\":\"subscribe\", \"resource\":\"/feeds/" "\"}"
    ws.send(msg)
    
ws = websocket.WebSocketApp(destUri,
 								on_message = on_message,
 								on_error = on_error,
 								on_close = on_close)
ws.on_open = on_open
ws.run_forever()
