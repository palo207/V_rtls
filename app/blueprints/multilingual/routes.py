# -*- coding: utf-8 -*-
"""
Created on Tue Jun 30 13:22:16 2020

@author: PAVA
"""
#import cv2
import os
import datetime
import hashlib, binascii
import random
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    make_response,
    session,
    Blueprint,
    g
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker 
from sqlalchemy import Column, Integer, String
from flask_sqlalchemy import SQLAlchemy
from flask_babel import _, refresh
from app import app
import config as c
import random

multilingual = Blueprint('multilingual', __name__, template_folder='templates')

# Database info
server = c.server
database = c.database
login = c.uid
passwd = c.password
driver = c.driver

# Global vars
rtls_tag_identifier = c.rtls_tag_identifier
scaling_factor_x = c.scaling_factor_x
scaling_factor_y = c.scaling_factor_y
x_prefix = c.x_prefix
y_prefix = c.x_prefix

# Choose version of locate
version = c.version

# Init of flask object
app.secret_key = c.secret_key

# MS Sql
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql://{}:{}@{}/{}?driver={}'.format(login,passwd,server,database,driver)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

def hash_password(password):
    # Hash a password for storing in db
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), 
                                salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')

def get_lang():
    if 'lang' in session and session.get('lang'):
        g.lang_code = session.get('lang')
        print('jazyk je en')
    else:
        g.lang_code = 'de'
        print('jazyk je sk')
    return g.lang_code


def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512', 
                                  provided_password.encode('utf-8'), 
                                  salt.encode('ascii'), 
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_password

class users(UserMixin, db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(50),unique=True)
    password = db.Column(db.String(500))

    def __init__(self,username, password):
        self.username = username
        self.password = password

class rtls_tags(db.Model):
    row_no = db.Column(db.Integer,primary_key=True)
    tag_id=db.Column(db.String(50))
    address=db.Column(db.String(50))
    PosX=db.Column(db.Float())
    PosY=db.Column(db.Float())
    zone_id=db.Column(db.String(50))
    zone_type=db.Column(db.String(50))
    zone_name=db.Column(db.String(50))
    zone_enter=db.Column(db.DateTime())
    paired=db.Column(db.Integer)
    paired_id=db.Column(db.String(50))

    def __init__(self,tag_id,object_id,edited_by):
        self.row_no=row_no
        self.tag_id=tag_id
        self.address=address
        self.PosX=PosX
        self.PosY=PosY
        self.zone_id=zone_id
        self.zone_type=zone_type
        self.zone_name=zone_name
        self.zone_enter=zone_enter
        self.paired=paired
        self.paired_id=paired_id

class logs(db.Model):
    row_no = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(50))
    type_of_change = db.Column(db.String(50))
    tag_id=db.Column(db.String(50))
    object_id=db.Column(db.String(50))

    def __init__(self,username,type_of_change,tag_id,object_id):
        self.username=username
        self.type_of_change=type_of_change
        self.tag_id=tag_id
        self.object_id=object_id

class tag_location(db.Model):
    row_no = db.Column(db.Integer,primary_key=True)
    tag_id=db.Column(db.String(50))
    x=db.Column(db.Integer)
    y=db.Column(db.Integer)

    def __init__(self,username,type_of_change,tag_id,object_id):
        self.tag_id=tag_id
        self.object_id=object_id

@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))

# Login page
@multilingual.route('/',methods=['GET','POST'])
def login():
    g.lang_code = get_lang()
    if request.method =='POST':
        username = request.form['username']
        password = request.form['password']
        user = users.query.filter_by(username=username).first()
        if user:
            vp = True
            vp = verify_password(user.password, password)
            if vp:
                login_user(user)
                return redirect(url_for('multilingual.Index'))
    return render_template('multilingual/login.html')


# Function returns tag data for location if the tag is in db
def get_tag_info(tag_id):
    tag_id=tag_id.upper()
    my_data_parsed=[]
    if tag_id.startswith(rtls_tag_identifier):
        my_data= db.session.query(rtls_tags).filter_by(tag_id=tag_id).first()
    else:
        my_data= db.session.query(rtls_tags).filter_by(paired_id=tag_id).first()
    
    # if my_data is None:

    #     #########################################
    #     try:
    #         dbcitosession = create_session()
    #         data = dbcitosession.query(tERPOrders).filter(tERPOrders.OrderSign==tag_id).first()
    #         dbcitosession.commit()
    #     except:
    #         dbcitosession.rollback()
    #     finally:
    #         dbcitosession.close()
    #     #########################################

    #     if data is None:
    #         return False,my_data_parsed
    #     else : 
    #         tag_id = str(data.Order_RId) + '-000000'
    #         my_data = db.session.query(rtls_tags).filter_by(paired_id=tag_id).first()
    
    if my_data is None:
        return False,my_data_parsed
   
    else:
        # if 'my_data' in session:
        #     session.pop('my_data', None)
        my_data_parsed.append( [my_data.tag_id,
                my_data.zone_id,
                my_data.zone_type,
                my_data.zone_name,
                my_data.zone_enter,
                my_data.paired_id,
                float(my_data.PosX),
                float(my_data.PosY)])
        return True,my_data_parsed


@app.login_manager.unauthorized_handler
def unauth_handler():
    return redirect(url_for('multilingual.login'))


# Logout button
@multilingual.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('multilingual.login'))

# RTLS Control page
@multilingual.route('/rtls_control')
@login_required
def Index():
    # Get all paired tags and render page with them
    try:
        i=request.args['i']
    except:
        i = 0
    try:
        code1=request.args['code1']
        code2=request.args['code2']
    except:
        code1 = 0
        code2 = 0

    if current_user.username in c.users:
        dsb="disabled"
    else:
        dsb=""

    g.lang_code = get_lang()

    # if 'my_data' in session and session.get('my_data'):
    #     mydata = session.get('my_data')
    #     tag_id=mydata[0][0]
    #     got_data,mydata=get_tag_info(tag_id)
    #     if got_data:
    #         mydata[0][6]= (mydata[0][6] + x_prefix) * scaling_factor_x 
    #         mydata[0][7]= (mydata[0][7] + y_prefix) * scaling_factor_y
    #         session['my_data']=mydata
    #         #################################################################
    #         #return render_template('multilingual/locate.html',mydata=mydata)
    #         ################################################################
    #     else:
    #         flash(_('Tag %(tag_id)s sa v databáze nenachádza', tag_id =tag_id), "error")
    # else:
    #     mydata=0

    return render_template('multilingual/Index.html',
                           user= current_user.username,
                           dsb=dsb,i=int(i),
                           code1=code1,
                           code2=code2,
                           mydata=0)


# Pair tag form
@multilingual.route('/insert',methods=['POST'])
def insert():
    g.lang_code = get_lang()
    if request.method == 'POST':
        tag_id = request.form['tag_id']
        tag_id = tag_id.upper()
        object_id = request.form['object_id']
        object_id = object_id.upper()
        tags =[]
        # One of barcodes has to start with RTLS identifier
        condition1 = tag_id.startswith(rtls_tag_identifier)
        condition2 = object_id.startswith(rtls_tag_identifier)
        if condition1:
            tags=[tag_id,object_id]
        elif condition2 :
            tags=[object_id,tag_id]

        # If fields are blank or conditions are not met
        if not (tag_id
            and object_id
            and (condition1 + condition2 == 1)
            ):
            flash(_('Nesprávne zadané vstupné dáta'), "error")
            return redirect(url_for('multilingual.Index'))

        # Condition 3 tag exists in database and is not paired
        condition3 = db.session.query(rtls_tags.paired).filter_by(tag_id=tags[0]).first()
        # Condition 4 object is not paired with tag
        condition4 = db.session.query(rtls_tags.paired_id).filter_by(paired_id=tags[1]).first()

        # If return is not none the tag does not exist in db
        if condition3 is None:
            flash(_('Tag sa v databáze nenachádza'), "error")
            return redirect(url_for('multilingual.Index'))
        
        # If tag is paired
        if condition3[0]:
            flash(_('Tag je už spárovaný'), "error")
            return redirect(url_for('multilingual.Index',i=1,code1=tags[0],code2=tags[1]))
        
        # If material is paired
        if condition4 is not None:
            flash(_('Výrobný príkaz už je spárovaný'), "error")
            return redirect(url_for('multilingual.Index',i=1,code2=tags[1],code1=tags[0]))

        # Getting the object from database
        tag=db.session.query(rtls_tags).filter_by(tag_id=tags[0]).first()
        # Pair tags
        tag.paired=1
        tag.paired_id=tags[1]
        log = logs(current_user.username,"pair",tags[0],tags[1])
        # Write ids and username into database
        db.session.commit()
        db.session.add(log)
        db.session.commit()

        flash(_('Výrobný príkaz už je spárovaný'))
        return redirect(url_for('multilingual.Index'))

# Unpair tag button next to pair tag button
@multilingual.route('/unpair',methods=['POST'])
def unpair():
    g.lang_code = get_lang()
    tag_id = request.form['tag_id']
    tag_id = tag_id.upper()
    # Delete tag and material pair
    my_data= db.session.query(rtls_tags).filter_by(tag_id=tag_id).first()
    if my_data is not None:
        my_data.paired=0
        my_data.paired_id="-"
        db.session.commit()
        log = logs(current_user.username,"unpair",tag_id,"")
        db.session.add(log)
        db.session.commit()
        flash(_('Tag %(tag_id)s bol úspešne odpárovaný', tag_id =tag_id))
        return redirect(url_for('multilingual.Index'))
    else:
        flash(_('Tag %(tag_id)s nie je spárovaný', tag_id =tag_id),"error")
        return redirect(url_for('multilingual.Index'))

# Contact
@multilingual.route('/contact')
def contact():
    return render_template('multilingual/contact.html')

# Change pair
@multilingual.route('/change_pair',methods=['POST'])
def change_pair():
    g.lang_code = get_lang()
    if request.method =='POST':
        codes = request.form['yes']
        if codes == "nie":
            return redirect(url_for('multilingual.Index'))
        else:
            codes = (codes.split("$,$"))
            try:
                my_data= db.session.query(rtls_tags).filter_by(paired_id=codes[1]).first()
                my_data.paired = 0
                my_data.paired_id="-"
                db.session.commit()
            except:
                print('Not in db') 

            my_data= db.session.query(rtls_tags).filter_by(tag_id=codes[0]).first()
            my_data.paired = 1
            my_data.paired_id=codes[1]
            db.session.commit()

            flash(_('Tag bol úspešne spárovaný'))
            return redirect(url_for('multilingual.Index'))

# Locate tag page
@multilingual.route ('/locate', methods = ['GET','POST'])
def locate():
    g.lang_code = get_lang()
    tag_id = request.form['tag_id']
    tag_id = tag_id.upper()
    
    # Calls get data to fetch data from db
    got_data,mydata = get_tag_info(tag_id)

    if got_data:
        mydata[0][6]= (mydata[0][6] + x_prefix) * scaling_factor_x 
        mydata[0][7]= (mydata[0][7] + y_prefix) * scaling_factor_y
        session['my_data']=mydata
        if version == 1:
        	return redirect(url_for('multilingual.Index',i=2))
        if version == 2:
            return redirect(url_for('multilingual.located', tag_id = tag_id))
                
    else:
        flash(_('Tag %(tag_id)s sa v databáze nenachádza', tag_id =tag_id), "error")
        return redirect(url_for('multilingual.Index'))

def generate_color():
    clr = []
    for i in range(0,3):
        b = random.randint(0,255)
        t = random.randint(0,255)
        if t>b:
            c = str(random.randint(b,t))
        elif t<b:
            c = str(random.randint(t,b))
        else:
            c = str(random.randint(0,255))
        clr.append(c)
    clr_code = "rgb({},{},{})".format(clr[0],clr[1],clr[2])
    return clr_code


@multilingual.route ('/locate_multiple', methods = ['GET','POST'])
def locate_multiple():
    loc_col_dict ={}
    g.lang_code = get_lang()
    collected_data = []
    try:
        tag_id = request.form['tag_id']
        tag_id = tag_id.upper()
        tag_ids = tag_id.split(' ')
        session['tag_ids'] = tag_ids
        session['tag_id'] = tag_id
    except:
        tag_id = session['tag_id']
        tag_ids = session['tag_ids']

    for id in tag_ids:
        got_data,mydata = get_tag_info(id)
        if got_data:
            mydata[0][6]= (mydata[0][6] + x_prefix) * scaling_factor_x 
            mydata[0][7]= (mydata[0][7] + y_prefix) * scaling_factor_y
            loc_key = str(mydata[0][6])+'#'+str(mydata[0][7])
            color = generate_color()
            if loc_key not in loc_col_dict.keys():
                loc_col_dict[loc_key]=color
                mydata[0].append(color)
            else:
                mydata[0].append(loc_col_dict[loc_key])

            collected_data.append(mydata)

    return render_template('multilingual/locate_multiple.html',
                                        collected_data=collected_data,
                                        tag_id=tag_id,
                                        user=current_user.username,
                                        api_address=c.api_address,
                                        refresh = c.refresh)
    
# If the localization process is successfull
@multilingual.route ('/located/<tag_id>',methods = ['GET','POST'])
def located(tag_id):
    g.lang_code = get_lang()
    mydata = session['my_data']
    return render_template('multilingual/locate.html',
                                        mydata=mydata,
                                        tag_id=tag_id,
                                        user=current_user.username,
                                        api_address=c.api_address,
                                        refresh = c.refresh)


@multilingual.route ('/get_location/<id>', methods = ['GET','POST'])
def get_location(id):
    tag_id = id
    tag_id = tag_id.upper()
    try:
        # Calls get data to fetch data from db
        got_data,mydata = get_tag_info(tag_id)
        mydata[0][6]= (mydata[0][6] + x_prefix) * scaling_factor_x 
        mydata[0][7]= (mydata[0][7] + y_prefix) * scaling_factor_y
        
        return render_template('multilingual/locate.html',
                                        mydata=mydata,tag_id=id)
    except: 
        return "Zadaný kód sa nenachádza v databáze"

@app.route("/get_pos/<id>")
def get_pos(id):
    # Calls get data to fetch data from db
    got_data,mydata = get_tag_info(id)
    
    if got_data:
        ypos=str((mydata[0][7] + y_prefix) *scaling_factor_y)+"%"
        xpos=str((mydata[0][6]+ x_prefix)* scaling_factor_x) +"%"
        tag_id=mydata[0][0]
        paired=mydata[0][5]
        zone=mydata[0][3]
        enter_zone=str(mydata[0][4])
        prod_no = "-"
        if paired != "-":
            paired_id = paired.split('-')[0]

            # If CITO is being used 
            # ################################################
            # try:
            #     dbcitosession = create_session()   
            #     data = dbcitosession.query(tERPOrders).filter(tERPOrders.Order_RId==paired_id).first()
            # except Exception as e:
            #     dbcitosession.rollback()
            #     return e
            # finally:
            #     dbcitosession.close()
            # ###################################################
           
            # if data is None:
            #     prod_no = "-"
            # else:
            #     prod_no = data.OrderSign
       
    else:
        ypos="50%"
        xpos="50%"
        tag_id="-"
        paired="-"
        zone="-"
        enter_zone="-"

    return jsonify(ypos=ypos,
                    xpos=xpos,
                    tag_id=tag_id,
                    paired=paired,
                    zone=zone,
                    enter_zone=enter_zone,
                    prod_no = prod_no)

@multilingual.route('/language/<lang>')
def language(lang):
    session['lang'] = lang
    return redirect(request.referrer)

@multilingual.route('/back',methods=['GET','POST'])
def back():
    return redirect(url_for('multilingual.Index'))

@multilingual.route('/_get_new_data', methods= ['GET','POST'])
def get_new_data():
    mydata = session.get('my_data')
    session['my_data']=mydata
    tag_id = mydata[0][0]
    got_data,my_data_parsed = get_tag_info(tag_id)
    return jsonify(PosX=my_data_parsed[0][6])
        
@multilingual.route('/paired')
def paired():
    my_data= db.session.query(rtls_tags).filter(rtls_tags.paired_id != "-").all()
    if my_data is None:
        return "Data not in database"
    my_data=[[x.tag_id,x.paired_id] for x in my_data]
    for i in range(0,len(my_data)):
        try:
            paired_id = int(my_data[i][1].split('-')[0])
        except:
            paired_id = 0

        # If CITO is being used 
        ###############################################    
        # try:
        #     dbcitosession = create_session()   
        #     data = dbcitosession.query(tERPOrders).filter(tERPOrders.Order_RId==paired_id).first()
        # except Exception as e:
        #     dbcitosession.rollback()
        #     return e
        # finally:
        #     dbcitosession.close()
        ###############################################

        # if data is None:
        #     my_data[i].append('-')
        # else:
        #     my_data[i].append(data.OrderSign)
        
    my_data[i].append('-')
    return jsonify(my_data)

@multilingual.route('/unpaired')
def unpaired():
    my_data= db.session.query(rtls_tags).filter(rtls_tags.paired_id == "-").all()
    if my_data is None:
        return "Data not in database"
    my_data=[[x.tag_id,x.paired_id] for x in my_data]
    return jsonify(my_data)

@multilingual.route('/all')
def all():
    my_data= db.session.query(rtls_tags).all()
    if my_data is None:
        return "Data not in database"
    my_data=[[x.tag_id,x.paired_id] for x in my_data]
    return jsonify(my_data)

@multilingual.route('/get_mac/<tag_id>')
def get_mac(tag_id):
    my_data= db.session.query(rtls_tags).filter(rtls_tags.tag_id == tag_id.upper()).first()
    if my_data is None:
        return "Not in database"
    return jsonify([my_data.tag_id,my_data.address])

@multilingual.route('/get_id/<mac>')
def get_id(mac):
    my_data= db.session.query(rtls_tags).filter(rtls_tags.address == mac).first()
    if my_data is None:
        return "Not in database"
    return jsonify([my_data.tag_id,my_data.address])

@multilingual.route('/create_user/<username>/<password>')
def create_user(username,password):
        try:
            password = hash_password(password)
            user= users(username = username, password = password)
            db.session.add(user)
            db.session.commit()
            return("User created sucesfully")
        except Exception as e:
            return('User already exists')


