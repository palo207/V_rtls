class Config(object):
    DEBUG = True
    LANGUAGES = ['en', 'de', 'sk']

# My pc db connect
server = "servername"
database = "dbname"
uid = 'username'
password = "pass"
driver = 'driver'

# Json parser
destUri = "ws://address:8080"
X_API_KEY = "x_api_key"

# Serve webapp
host='address to serve'
port=2500

# Address of locate api
# Testing
api_address = "http://127.0.0.1:5000"
# Production
# api_address = "http://" + host + ":" +str(port)


# Refresh of located
refresh = 1000

# Global vars
rtls_tag_identifier = "RTLS_TAG_"
scaling_factor_x = 0.78
scaling_factor_y = 1.742
x_prefix = -3.5
y_prefix = -3.4

# Choose version of locate
version = 2

# Init of flask object
secret_key = "secretkey"

# Software zone jumps
soft_zone_jumps = {
                    'sample':[7.38,20.34],
                  }

# Users who cannot pair, unpair
users = ['user']
