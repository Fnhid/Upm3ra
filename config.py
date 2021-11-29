db = {
    'user'     : 'root',
    'password' : 'toor',
    'host'     : 'raspberrypi.mshome.net',
    'port'     : '3306',
    'database' : 'upm3ra'
}

DB_URL = f"mysql+mysqlconnector://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}?charset=utf8" 