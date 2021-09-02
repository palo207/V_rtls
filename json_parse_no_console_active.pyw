"""
Created on Wed Jun 10 13:37:29 2020

@author: PAVA
"""
import os
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
                    server,
                    soft_zone_jumps)
import pandas as pd

# Check if zone is an exit zone
def check_if_exit(zone_name):
    return zone_name.startswith('X')

# Get location of zone to place tag on layout
def get_outside_loc(old_zone_name,zone_name):
    if zone_name in soft_zone_jumps.keys():
        x = soft_zone_jumps[zone_name][0]
        y =soft_zone_jumps[zone_name][1]
        return True,x,y
    else:
        return False,0,0

# Read names and mac from excel
data=pd.read_excel("rtls_tag_names.xlsx", header=None)
tag_ids = list(data.iloc[:,1])
mac_addr = list(data.iloc[:,9])
dict_of_tags = {}
for id in range(0,len(tag_ids),1):
    dict_of_tags[mac_addr[id]]=tag_ids[id]
    
# Handle exception and write into log_file
def f_handle_exception(e,SQLCommand,message):
    log = open('log.txt','a+')
    if os.stat(r"log.txt").st_size > 500000000:
        log.truncate(0)
    log_date = datetime.now()
    log.write("{} {} {} {} \n\n".format(log_date,e,SQLCommand,message))
    log.close()
    return 0

# Handles incoming json messages   
def write_data_db(message,
                    driver=driver,
                    server=server,
                    database=database,
                    uid=uid,
                    password=password):
    
    # Phase 1 - check if connection is ok
    try:
        cnxn = pyodbc.connect(driver="{}".format(driver),
                        server=server, 
                        database=database,               
                        uid=uid,
                        password=password)
        
    except Exception as e:
        log = open('log.txt','a')
        log_date = datetime.now()
        log.write("{} {} \n\n".format(log_date,e))
        return 0
    
    # Phase 2 - check if data is ok
    try:
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
    except:
        return 0

    # Take cnxn object, handle insert, selects, updates and close conn
    try:
        with cnxn:
            cursor = cnxn.cursor()
            
            # Phase 3 - check if zone is in body of json
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

            # Check current zone of tag
            zone_enter = datetime.now().replace(microsecond=0)
            SQLCommand = ("SELECT TOP 1 zone_name from {}.dbo.rtls_tags WHERE tag_id = ?".format(database))
            Values = [tag_id]
            try:
                cursor.execute(SQLCommand, Values)
                result = cursor.fetchall()
            except Exception as e:
                return f_handle_exception(e,SQLCommand,message)

            # If the tag is already in the database - update
            if result:
                old_zone_name  = str(result[0][0])  
                # If zone is the same or actual zone is 0 it will not be updated 
                if (old_zone_name == zone_name) or (zone_name == "0"):
                    SQLCommand = ("UPDATE {}.dbo.rtls_tags SET address = ?, PosX =?, PosY = ?, zone_id = ?, zone_type = ?, zone_name = ? WHERE tag_id = ?".format(database))
                    Values = [address, posx, posy, zone_id, zone_type, old_zone_name, tag_id]
                    try:
                        cursor.execute(SQLCommand, Values)
                        cnxn.commit()
                    except Exception as e:
                        return f_handle_exception(e,SQLCommand,message)
                
                # If the zones differ
                else:
                    # If the zone is exit zone
                    
                    try:
                        # Check if zone is virtual
                        status,mx,my = get_outside_loc(old_zone_name,zone_name)
                        if status:
                            posx,posy = mx,my
                    except:
                        pass

                    # If it is not exit zone
                    SQLCommand = ("UPDATE {}.dbo.rtls_tags SET address = ?, PosX =?, PosY = ?, zone_id = ?, zone_type = ?, zone_name = ?, zone_enter = ?  WHERE tag_id = ?".format(database))
                    Values = [address, posx, posy, zone_id, zone_type, zone_name, zone_enter, tag_id]
                    try:
                        cursor.execute(SQLCommand, Values)
                        cnxn.commit()
                    except Exception as e:
                        return f_handle_exception(e,SQLCommand,message)

                # Update locagtion of tag in tag_location table
                SQLCommand = ("UPDATE {}.dbo.tag_location SET x=?,y=? WHERE tag_id = ?".format(database))
                Values = [float_posx,float_posy,tag_id]
                try:
                    cursor.execute(SQLCommand, Values)
                    cnxn.commit()
                except Exception as e:
                    return f_handle_exception(e,SQLCommand,message)

            # If the tag is not in the db insert new
            else:
                #print('inserting new tag into db')
                SQLCommand = ("INSERT INTO {}.dbo.rtls_tags(tag_id, address, PosX, PosY, zone_id, zone_type, zone_name, zone_enter, paired, paired_id) VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(database))
                Values = [tag_id,
                            address, 
                            posx, 
                            posy, 
                            zone_id, 
                            zone_type, 
                            zone_name, 
                            zone_enter, 
                            0, 
                            '-' ]
                #print(Values)
                try:
                    cursor.execute(SQLCommand, Values)
                    cnxn.commit()
                except Exception as e:
                    return f_handle_exception(e,SQLCommand,message)

                # Insert new tag location into table
                SQLCommand = ("INSERT INTO {}.dbo.tag_location(tag_id,x,y) VALUES(?, ?, ?)".format(database))
                Values = [tag_id,  float_posx, float_posy]
                try:
                    cursor.execute(SQLCommand, Values)
                    cnxn.commit()
                except Exception as e:
                    return f_handle_exception(e,SQLCommand,message)
    
    # If crashes, write into log and return 0
    except Exception as e:
        log = open('log.txt','a')
        log_date = datetime.now()
        log.write("{} {} \n\n".format(log_date,e))
        return 0

def on_message(ws, message):
    print(message)
    try:
        write_data_db(message=message)
    except Exception as e:
        log = open('log.txt','a')
        log_date = datetime.now()
        log.write("{} {} {} \n\n".format(log_date,e,message))

def on_error(ws, error):
    print (error)
    log = open('log.txt','a')
    log_date = datetime.now()
    log.write(" {} {} \n\n".format(error,log_date))

def on_close(ws):
    print ("### closed ###")

def on_open(ws):
    print ("### opened ###")
    msg = "{\"headers\":{\"X-ApiKey\":\""+ X_API_KEY +"\"},\"method\":\"subscribe\", \"resource\":\"/feeds/" "\"}"
    ws.send(msg)
    
ws = websocket.WebSocketApp(destUri,
 								on_message = on_message,
 								on_error = on_error,
 								on_close = on_close,
                                on_open = on_open)
while True:
    ws.run_forever()
