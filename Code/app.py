from configparser import ConfigParser

from flask import Flask, jsonify, request
import psycopg2
import jwt
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Th1s1ss3cr3t'


def token_required(token):
    if not token:
        return jsonify({'message': 'Token is missing!'}), 403
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"]), 200
    except:
        return jsonify({'message': 'Token is invalid!'}), 403


def getDBConfigs(filename='DBConfig.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/user/<username>,<email>,<password>', methods=['GET'])
def register(username, email, password):
    message = {"user": username, "pass": password, "mail": email}
    return jsonify(message)


@app.route('/user/<username>,<password>', methods=['PUT'])
def login(username, password):
    conn = None

    # warnings.filterwarnings("ignore")
    try:
        params = getDBConfigs()

        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params)  # creates connection with the data base

        # create a cursor ( a cursor is the command that "talks" with the database")
        cur = conn.cursor()
        isLogin = True  # mudar isto para checkar se existe
        if isLogin:
            token = jwt.encode({'user': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                               app.config['SECRET_KEY'], algorithm="HS256")
            cur.close()
            conn.commit()
            return jsonify({'token': token})
        else:
            cur.close()
            conn.commit()
            return "ERROR"  # por codigo de erro aqui
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


@app.route('/leilao/<artigoId>', methods=['GET'])
def criarLeilao(artigoId):
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        user = l['user']
    # mudar isto para criar com a BD
    return artigoId


if __name__ == '__main__':
    app.run(debug=True)
