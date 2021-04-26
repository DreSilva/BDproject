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


@app.route('/user/<username>,<email>,<password>', methods=['POST'])
def register(username, email, password):
    conn = None

    try:
        params = getDBConfigs()

        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params)  # creates connection with the data base

        # create a cursor ( a cursor is the command that "talks" with the database")
        cur = conn.cursor()
        cur.execute("Begin Transaction")
        cur.execute("Insert into pessoa(username,email,password,admin,banned) values(%s,%s,%s,false,false )",
                    (username, email, password))
        cur.execute("Select userid from pessoa where username=%s and password=%s", (username, password))
        id = cur.fetchall()
        cur.execute("commit")
        message = {"userId": id[0][0]}
        return message

    except (Exception, psycopg2.DatabaseError) as error:
        if isinstance(error, psycopg2.errors.UniqueViolation):
            message = {"Code": 409, "error": "User or email already exists"}
            return jsonify(message)

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


@app.route('/user/<username>,<password>', methods=['PUT'])
def login(username, password):
    conn = None
    try:
        params = getDBConfigs()

        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params)  # creates connection with the data base

        # create a cursor ( a cursor is the command that "talks" with the database")
        cur = conn.cursor()
        cur.execute("Select * from pessoa where username=%s and password=%s", (username, password))
        isLogin = cur.fetchall()
        if isLogin:
            token = jwt.encode({'user': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                               app.config['SECRET_KEY'], algorithm="HS256")
            cur.close()
            conn.commit()
            return jsonify({'token': token})
        else:
            cur.close()
            conn.commit()
            message = {"Code": 403, "error": "Wrong user or password"}
            return jsonify(message)

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


@app.route('/leilao/<artigoId>', methods=['GET'])  # falta acabar
def criarLeilao(artigoId):
    # Copiar isto para saber se o user tem token ou nao
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        user = l['user']
    # fazer o resto aqui


@app.route('/leiloes', methods=['GET'])  # falta testar isto
def listarLeiloes():
    # Copiar isto para saber se o user tem token ou nao
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        try:
            params = getDBConfigs()

            # connect to the PostgreSQL server
            conn = psycopg2.connect(**params)  # creates connection with the data base

            # create a cursor ( a cursor is the command that "talks" with the database")
            cur = conn.cursor()
            cur.execute("Select leilaoid,descricao from leilao")
            leiloes = cur.fetchall()
            lista = []
            for leilao in leiloes:
                message = {"leilaoId": leilao[0], "descricao": leilao[1]}
                lista.append(message)
            return jsonify(lista)

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/atividade', methods=['GET'])  # falta testar isto
def listarAtividade():
    # Copiar isto para saber se o user tem token ou nao
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        user = l['user']
        try:
            params = getDBConfigs()

            # connect to the PostgreSQL server
            conn = psycopg2.connect(**params)  # creates connection with the data base

            # create a cursor ( a cursor is the command that "talks" with the database")
            cur = conn.cursor()
            cur.execute("begin transaction")
            cur.execute("Select userid from pessoa where username=%s", (user, ))
            id = cur.fetchall()[0]
            cur.execute("Select leilaoid,descricao from leilao where pessoa_userid = %s", id) # obter leiloes onde o user e o criador
            leiloes = cur.fetchall()
            lista = []
            for leilao in leiloes:
                message = {"leilaoId": leilao[0], "descricao": leilao[1], "role": "Criador"}
                lista.append(message)
            cur.execute("Select leilao_leilaoid from licitacao where pessoa_userid = %s", id)
            licitacoes = cur.fetchall()
            for licitacao in licitacoes:
                cur.execute("Select leilaoid,descricao from leilao where leilaoid = %s", licitacao)
                leilao = cur.fetchall()
                message = {"leilaoId": leilao[0], "descricao": leilao[1], "role": "Licitador"}
                lista.append(message)

            return jsonify(lista)

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


if __name__ == '__main__':
    app.run(debug=True)
