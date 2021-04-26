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


@app.route('/user', methods=['POST'])
def register():
    conn = None

    try:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
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


@app.route('/user', methods=['PUT'])
def login():
    conn = None
    try:
        username = request.form['username']
        password = request.form['password']
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


@app.route('/leilao', methods=['GET'])  # falta acabar
def criarLeilao():
    # Copiar isto para saber se o user tem token ou nao
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        try:
            params = getDBConfigs()
            conn = psycopg2.connect(**params)
            cur = conn.cursor()

            #obter o userId
            username = l['user']#usar para ir buscar os userid
            #cur.execute("Select * from pessoa where username = %s", (username))
            cur.execute("Select * from pessoa where username=%s", (username,))
            user_stats = cur.fetchall()

            userId = user_stats[0][0]
            artigoId = request.form['artigoId']
            precoMinimo = request.form['precoMinimo']
            titulo = request.form['titulo']
            descricao = request.form['descricao']
            dataFim = request.form['dataFim']#data no formato yyyy-mm-dd h:min
            dataInicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            #agora temos toda a informacao para criar o leilao
            cur.execute("begin")
            cur.execute("Insert into leilao(artigoId, precominimo, titulo, descricao, datainicio, datafim, cancelado, pessoa_userid) values(%s, %s, %s, %s, %s, %s, false, %s)", (artigoId, precoMinimo, titulo, descricao, dataInicio, dataFim, userId))
            cur.execute("select * from leilao where artigoid = %s", (artigoId))
            leilaoId = cur.fetchall()[0][0]
            cur.execute("commit")

            message = {"leilaoId" : leilaoId}
            return jsonify(message)
        except(Exception, psycopg2.DatabaseError) as error:
            if isinstance(error, psycopg2.errors.UniqueViolation):
                message = {"Code": 409, "error": "artigo ja existe na base de dados."}
                return jsonify(message)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')
        


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
