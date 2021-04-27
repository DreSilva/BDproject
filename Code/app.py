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


@app.route('/leilao', methods=['POST'])  # falta acabar
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
            cur.execute("select * from leilao where artigoid = %s", (artigoId,))
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


@app.route('/leiloes/<keyword>', methods = ['GET'])
def listarLeiloesKeyword(keyword):
    #a keyword pode tanto ser uma descricao como um codigo EAN/ISBN
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        try:
            params = getDBConfigs()
            conn = psycopg2.connect(**params)
            cur = conn.cursor()

            try:#se for um numero tanto pode ser um artigoId como algo da descricao, logo pesquisa-se ambos.
                int(keyword)
                flag = 1
            except(Exception) as error:#nao e um numero
                flag = 0

            cur.execute('begin')
            if flag == 1:
                cur.execute("select leilaoid, descricao from leilao where artigoid = %s or descricao = %s", (keyword, keyword))
            else:
                cur.execute("select leilaoid, descricao from leilao where descricao = %s", (keyword,))
            leiloes = cur.fetchall()
            cur.execute('commit')

            lei_list = []
            for leilao in leiloes:
                message = {'leilaoId': leilao[0], 'descricao': leilao[1]}
                lei_list.append(message)
            
            return jsonify(lei_list)

        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
        
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/leilao/<leilaoId>', methods = ['PUT'])
def editarLeilao(leilaoId):
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        username = l['user']#para saber se este leilao e deste user
        
        try:
            params = getDBConfigs()
            conn = psycopg2.connect(**params)
            cur = conn.cursor()

            cur.execute("select userid from pessoa where username = %s", (username,))
            userId = cur.fetchall()[0][0]

            cur.execute("select pessoa_userid from leilao where leilaoid = %s", (leilaoId,))
            pessoa_userId = cur.fetchall()[0][0]

            if userId != pessoa_userId:#o user nao e o criador do leilao, logo nao o pode alterar
                return jsonify({"erro": "nao e o criador do leilao."})

            #assumo que algum deles possa ser uma string vazia
            titulo = request.form['titulo']
            descricao = request.form['descricao']

            #se algum dos campos tiver conteudo, tem de ser registado (versao) o titulo e a descricao antiga
            if titulo != "" or descricao != "":
                cur.execute('begin')
                #obter os valores atuais
                cur.execute("select titulo, descricao from leilao where leilaoid = %s", (leilaoId,))
                past_info = cur.fetchall()

                #obter o ultimo numero de versao utilizado
                cur.execute("select versao from versao where leilao_leilaoid = %s order by versao desc", (leilaoId))
                aux = cur.fetchall()

                if aux == []:
                    last_version = 0
                else:
                    last_version = int(aux[0][0])

                #criar registo na tabela versao
                #so adiciona se o titulo ou descricao forem diferentes do que ja la estao
                if past_info[0][0] != titulo and titulo != "" or past_info[0][1] != descricao and descricao != "":
                    cur.execute("insert into versao (versao, titulo, descricao, leilao_leilaoid) values(%s, %s, %s, %s)", (str(last_version + 1), past_info[0][0], past_info[0][1], leilaoId))

                #atualizar informacao do leilao
                if titulo != "" and descricao != "":
                    cur.execute("update leilao set (titulo, descricao) = (%s, %s) where leilaoid = %s", (titulo, descricao, leilaoId))
                elif titulo == "":#titulo vazio
                    cur.execute("update leilao set descricao = %s where leilaoid = %s", (descricao, leilaoId))
                elif descricao == "":#decricao vazia
                    cur.execute("update leilao set titulo = %s where leilaoid = %s", (titulo, leilaoId))
                
                #obter info atual do leilao
                cur.execute("select * from leilao where leilaoid = %s", (leilaoId,))
                current_info = cur.fetchall()[0]
                message = {"leilaoId": current_info[0], "precoMinimo": current_info[1], "artigoId": current_info[2], "titulo": current_info[3], "descricao": current_info[4], "dataFim": current_info[5], "cancelado": current_info[6], "dataInicio": current_info[7], "pessoa_userId": current_info[8]}
                cur.execute('commit')
            else:
                #Todo nao sei que codigo colocar aqui, considero que da erro se ambos os parametros forem ""
                message = {"erro": "sem dados para alterar."}
            return jsonify(message)
        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
        
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/licitacao', methods=['POST'])
def criarLicitacao():
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


            if user_stats[0][5]:
                pessoa_userId = user_stats[0][0]
                leilao_leilaoid = request.form['leilao_leilaoid']
                valor = request.form['valor']

                cur.execute("Select * from leilao where leilaoid=%s", (leilao_leilaoid))
                leilao_stats = cur.fetchall()
                if leilao_stats[0][5]:
                    #agora temos toda a informacao para criar o licitação
                    cur.execute("begin")
                    cur.execute("Insert into licitacao( valor, valida, leilao_leilaoid, pessoa_userid) values( %s, true, %s, %s)", ( valor, leilao_leilaoid, pessoa_userId))
                    cur.execute("select * from licitacao where leilao_leilaoid = %s and pessoa_user_id = %s order by valor DESC", (leilao_leilaoid,pessoa_userId))
                    licitacaoId = cur.fetchall()[0][0]
                    cur.execute("commit")

                    message = {"licitacaoId" : licitacaoId}
                    return jsonify(message)
                else:
                    message = {"Code": 403, "error": "o leilão já terminou"}
                    return jsonify(message)
            else:
                message = {"Code": 403, "error": "o utilizador foi banido."}
                return jsonify(message)

        except(Exception, psycopg2.DatabaseError) as error:
            if isinstance(error, psycopg2.errors.UniqueViolation):
                message = {"Code": 409, "error": "artigo ja existe na base de dados."}
                return jsonify(message)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


if __name__ == '__main__':
    app.run(debug=True)
