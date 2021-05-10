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


@app.route('/leilao', methods=['POST'])
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

            # obter o userId
            username = l['user']  # usar para ir buscar os userid
            # cur.execute("Select * from pessoa where username = %s", (username))
            cur.execute("Select * from pessoa where username=%s", (username,))
            user_stats = cur.fetchall()

            userId = user_stats[0][0]
            artigoId = request.form['artigoId']
            precoMinimo = request.form['precoMinimo']
            titulo = request.form['titulo']
            descricao = request.form['descricao']
            dataFim = request.form['dataFim']  # data no formato yyyy-mm-dd h:min
            dataInicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            # agora temos toda a informacao para criar o leilao
            cur.execute("begin")
            cur.execute(
                "Insert into leilao(artigoId, precominimo, titulo, descricao, datainicio, datafim, cancelado, pessoa_userid) values(%s, %s, %s, %s, %s, %s, false, %s)",
                (artigoId, precoMinimo, titulo, descricao, dataInicio, dataFim, userId))
            cur.execute("select * from leilao where artigoid = %s", (artigoId,))
            leilaoId = cur.fetchall()[0][0]
            cur.execute("commit")

            message = {"leilaoId": leilaoId}
            return jsonify(message)
        except(Exception, psycopg2.DatabaseError) as error:
            if isinstance(error, psycopg2.errors.UniqueViolation):
                message = {"Code": 409, "error": "artigo ja existe na base de dados."}
                return jsonify(message)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/leiloes', methods=['GET'])
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


@app.route('/atividade', methods=['GET'])  
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
            cur.execute("Select userid from pessoa where username=%s", (user,))
            id = cur.fetchall()[0]
            cur.execute("Select leilaoid,descricao from leilao where pessoa_userid = %s",
                        id)  # obter leiloes onde o user e o criador
            leiloes = cur.fetchall()
            lista = []
            for leilao in leiloes:
                message = {"leilaoId": leilao[0], "descricao": leilao[1], "role": "Criador"}
                lista.append(message)
            cur.execute("Select DISTINCT leilao_leilaoid from licitacao where pessoa_userid = %s", id)
            licitacoes = cur.fetchall()
            for licitacao in licitacoes:
                cur.execute("Select leilaoid,descricao from leilao where leilaoid = %s", licitacao)
                leiloes = cur.fetchall()
                for leilao in leiloes:
                    message = {"leilaoId": leilao[0], "descricao": leilao[1], "role": "Licitador"}
                    lista.append(message)

            return jsonify(lista)

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/leiloes/<keyword>', methods=['GET'])
def listarLeiloesKeyword(keyword):
    # a keyword pode tanto ser uma descricao como um codigo EAN/ISBN
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        try:
            params = getDBConfigs()
            conn = psycopg2.connect(**params)
            cur = conn.cursor()

            try:  # se for um numero tanto pode ser um artigoId como algo da descricao, logo pesquisa-se ambos.
                int(keyword)
                flag = 1
            except(Exception) as error:  # nao e um numero
                flag = 0

            cur.execute('begin')
            if flag == 1:
                cur.execute("select leilaoid, descricao from leilao where artigoid = %s or descricao = %s",
                            (keyword, keyword))
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


@app.route('/leilao/<leilaoId>', methods=['PUT'])
def editarLeilao(leilaoId):
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        username = l['user']  # para saber se este leilao e deste user

        try:
            params = getDBConfigs()
            conn = psycopg2.connect(**params)
            cur = conn.cursor()

            cur.execute("select userid from pessoa where username = %s", (username,))
            userId = cur.fetchall()[0][0]

            cur.execute("select pessoa_userid from leilao where leilaoid = %s", (leilaoId,))
            pessoa_userId = cur.fetchall()[0][0]

            if userId != pessoa_userId:  # o user nao e o criador do leilao, logo nao o pode alterar
                return jsonify({"erro": "nao e o criador do leilao."})

            # assumo que algum deles possa ser uma string vazia
            titulo = request.form['titulo']
            descricao = request.form['descricao']

            # se algum dos campos tiver conteudo, tem de ser registado (versao) o titulo e a descricao antiga
            if titulo != "" or descricao != "":
                cur.execute('begin')
                # obter os valores atuais
                cur.execute("select titulo, descricao from leilao where leilaoid = %s", (leilaoId,))
                past_info = cur.fetchall()

                # obter o ultimo numero de versao utilizado
                cur.execute("select versao from versao where leilao_leilaoid = %s order by versao desc", (leilaoId))
                aux = cur.fetchall()

                if aux == []:
                    last_version = 0
                else:
                    last_version = int(aux[0][0])

                # criar registo na tabela versao
                # so adiciona se o titulo ou descricao forem diferentes do que ja la estao
                if past_info[0][0] != titulo and titulo != "" or past_info[0][1] != descricao and descricao != "":
                    cur.execute(
                        "insert into versao (versao, titulo, descricao, leilao_leilaoid) values(%s, %s, %s, %s)",
                        (str(last_version + 1), past_info[0][0], past_info[0][1], leilaoId))

                # atualizar informacao do leilao
                if titulo != "" and descricao != "":
                    cur.execute("update leilao set (titulo, descricao) = (%s, %s) where leilaoid = %s",
                                (titulo, descricao, leilaoId))
                elif titulo == "":  # titulo vazio
                    cur.execute("update leilao set descricao = %s where leilaoid = %s", (descricao, leilaoId))
                elif descricao == "":  # decricao vazia
                    cur.execute("update leilao set titulo = %s where leilaoid = %s", (titulo, leilaoId))

                # obter info atual do leilao
                cur.execute("select * from leilao where leilaoid = %s", (leilaoId,))
                current_info = cur.fetchall()[0]
                message = {"leilaoId": current_info[0], "precoMinimo": current_info[1], "artigoId": current_info[2],
                           "titulo": current_info[3], "descricao": current_info[4], "dataFim": current_info[5],
                           "cancelado": current_info[6], "dataInicio": current_info[7],
                           "pessoa_userId": current_info[8]}
                cur.execute('commit')
            else:
                # Todo nao sei que codigo colocar aqui, considero que da erro se ambos os parametros forem ""
                message = {"erro": "sem dados para alterar."}
            return jsonify(message)
        except(Exception, psycopg2.DatabaseError) as error:
            print(error)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/licitar/<leilaoid>/<licitacao>', methods=['GET'])
def criarLicitacao(leilaoid, licitacao):
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

            # obter o userId
            username = l['user']  # usar para ir buscar os userid
            # cur.execute("Select * from pessoa where username = %s", (username))
            cur.execute("Select * from pessoa where username=%s", (username,))
            user_stats = cur.fetchall()

            if not user_stats[0][5]:
                pessoa_userId = user_stats[0][0]
                leilao_leilaoid = int(leilaoid)
                valor = int(licitacao)

                cur.execute("begin")
                cur.execute("Select * from leilao where leilaoid=%s", (leilao_leilaoid,))
                leilao_stats = cur.fetchall()
                cur.execute("Select * from licitacao where leilao_leilaoid = %s order by valor DESC",(leilao_leilaoid, ))

                licitacao_stat = cur.fetchall()

                if leilao_stats[0][8] == pessoa_userId:
                    message = {"Code": 403, "error": "Não pode votar no seu proprio Leilão"}
                    cur.execute("commit")
                    return jsonify(message)

                if licitacao_stat:
                    valorAlto = licitacao_stat[0][1]

                    if valor < valorAlto:
                        message = {"Code": 403, "error": "Licitacao mais baixa que a atual. Aumente o valor."}
                        cur.execute("commit")
                        return jsonify(message)
                    elif valor == valorAlto:
                        message = {"Code": 403, "error": "Licitacao igual à atual. Aumente o valor."}
                        cur.execute("commit")
                        return jsonify(message)
                    #else: #TODO Testar isto
                        #notificacaoLicitacao(pessoa_userId, leilao_leilaoid, valor)
                        #tem de ser criado um trigger para desempenhar esta funcao

                else:
                    if valor < leilao_stats[0][1]:
                        message = {"Code": 403, "error": "Licitacao mais baixa que o valor minimo"}
                        cur.execute("commit")
                        return jsonify(message)


                if leilao_stats[0][5] > datetime.datetime.utcnow() and not leilao_stats[0][6]:
                    # agora temos toda a informacao para criar o licitação

                    cur.execute(
                        "Insert into licitacao( valor, valida, leilao_leilaoid, pessoa_userid) values( %s, true, %s, %s)",
                        (valor, leilao_leilaoid, pessoa_userId))
                    cur.execute(
                        "select * from licitacao where leilao_leilaoid = %s and pessoa_userid = %s order by valor DESC",
                        (leilao_leilaoid, pessoa_userId))
                    licitacaoId = cur.fetchall()[0][0]
                    cur.execute("commit")

                    message = {"licitacaoId": licitacaoId}
                    return jsonify(message)
                else:
                    cur.execute("commit")
                    message = {"Code": 403, "error": "o leilão já terminou"}
                    return jsonify(message)
            else:
                message = {"Code": 403, "error": "o utilizador foi banido."}
                return jsonify(message)

        except(Exception, psycopg2.DatabaseError) as error:

            if isinstance(error, psycopg2.errors.UniqueViolation):
                message = {"Code": 409, "error": "Valor ja existe na base de dados."}
                return jsonify(message)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/leilao/<leilaoid>', methods=['GET'])
def detalhesLeilao(leilaoid):
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

            # obter o userId
            username = l['user']  # usar para ir buscar os userid

            cur.execute("begin transaction")
            cur.execute("Select * from leilao where leilaoid = %s", (leilaoid, ))
            infoLeilao = cur.fetchall()[0]
            cur.execute("Select * from licitacao where leilao_leilaoid = %s order by valor DESC", (leilaoid,))
            infoLicitacao = cur.fetchall()
            cur.execute("Select * from comentario where leilao_leilaoid = %s", (leilaoid,))
            infoComments = cur.fetchall()
            cur.execute("Select * from versao where leilao_leilaoid = %s", (leilaoid,))
            infoVersao = cur.fetchall()
            cur.execute("commit")

            listInfo = []

            message = {"leilaoId": infoLeilao[0], "precoMinimo": infoLeilao[1], "artigoId": infoLeilao[2],
                       "titulo": infoLeilao[3], "descricao": infoLeilao[4], "dataFim": infoLeilao[5],
                       "cancelado": infoLeilao[6], "dataInicio": infoLeilao[7],
                       "dono": infoLeilao[8]}
            listInfo.append(message)

            for licitacao in infoLicitacao:
                message = {"licitacaoId": licitacao[0], "valor": licitacao[1], "valida": licitacao[2]}
                listInfo.append(message)

            for comment in infoComments:
                message = {"comentarioId": comment[0], "comentario": comment[0], 'comentadorId': comment[3]}
                listInfo.append(message)

            for versao in infoVersao:
                message = {"versao": versao[0], "titulo": versao[1], "descricao":versao[2]}
                listInfo.append(message)

            return jsonify(listInfo)

        except(Exception, psycopg2.DatabaseError) as error:
            if isinstance(error, psycopg2.errors.UniqueViolation):
                message = {"Code": 409, "error": "Valor ja existe na base de dados."}
                return jsonify(message)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


@app.route('/comentário', methods=['POST'])
def comentarLeilao(): #TODO testar esta func toda
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

            # obter o userId
            username = l['user']  # usar para ir buscar os userid
            # cur.execute("Select * from pessoa where username = %s", (username))
            cur.execute("Select * from pessoa where username=%s", (username,))
            user_stats = cur.fetchall()

            userId = user_stats[0][0]
            leilaoid = request.form['leilaoid']
            comentario = request.form['comentario']

            # agora temos toda a informacao para criar o leilao
            cur.execute("begin")
            cur.execute("Insert into comentario(comentario, leilao_leilaoid, pessoa_userid) values(%s, %s, %s)", (comentario, leilaoid, userId))
            cur.execute("select * from comentario where  comentario = %s and leilao_leilaoid = %s and pessoa_userid =%s", (comentario,leilaoid,userId))
            comentarioId = cur.fetchall()[0][0]
            cur.execute("commit")

            message = {"comentarioid": comentarioId}
            return jsonify(message)
        except(Exception, psycopg2.DatabaseError) as error:
            if isinstance(error, psycopg2.errors.UniqueViolation):
                message = {"Code": 409, "error": "artigo ja existe na base de dados."}
                return jsonify(message)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')

def notificacaoLicitacao(pessoa_userId, leilaoId, value):
    #pessoa_userId -> id de quem fez a licitacao
    #leilaoId -> leilao no qual a licitacao foi efetuada
    #value -> valor da licitacao

    conn = None
    try:
        params = getDBConfigs()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        
        #obter as pessoas que licitaram no leilao
        cur.execute("begin")
        cur.execute("select distinct pessoa_userid from licitacao where leilao_leilaoid = %s and pessoa_userid <> %s", (leilaoId, pessoa_userId))
        users = cur.fetchall()
        print(users)
        if users != []:#houve licitacoes no leilao(sem ser a do user atual)
            #mandar a notificacao
            message = "There's been a better bid on the auction number {}, with value {}.".format(leilaoId, value)
            for user in users:
                cur.execute('insert into notificacao (mensagem, pessoa_userid) values(%s, %s)', (message, user[0]))
        cur.execute("commit")
    except(Exception, psycopg2.DatabaseError) as error:
            print(error)
    finally:
        if conn:
            conn.close()
            print('Database connection is closed.')


@app.route('/caixamensagens', methods=['GET'])
def caixaMensagens():
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    else:
        conn = None
        try:
            params = getDBConfigs()
            conn = psycopg2.connect(**params)
            cur = conn.cursor()
            username = l['user']
            cur.execute("begin")
            cur.execute("Select userid from pessoa where username=%s ", (username,))
            userid = cur.fetchall()[0]

            cur.execute("Select * from notificacao where pessoa_userid=%s", userid)
            notificacoes = cur.fetchall()

            cur.execute("Select leilaoid,descricao from leilao where pessoa_userid = %s", userid)  # obter leiloes onde o user e o criador
            leiloes = cur.fetchall()

            cur.execute("Select DISTINCT leilao_leilaoid from licitacao where pessoa_userid = %s", userid)
            licitacoes = cur.fetchall()
            lista = []

            for notificaco in notificacoes:
                message = {'tipo': 'Notificação','mensagem': notificaco[0]}
                lista.append(message)

            for leilao in leiloes:
                cur.execute("Select * from comentario where leilao_leilaoid=%s", (leilao[0], ))
                mural = cur.fetchall()
                for comment in mural:
                    message = {'tipo': 'Mural Criador','mensagem':comment[1]}
                    lista.append(message)

            for licitacao in licitacoes:
                cur.execute("Select * from comentario where leilao_leilaoid=%s", licitacao)
                mural = cur.fetchall()
                for comment in mural:
                    message = {'tipo': 'Mural Licitador', 'mensagem': comment[1]}
                    lista.append(message)

            cur.execute("commit")
            return jsonify(lista)

        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
        finally:
            if conn:
                conn.close()
                print('Database connection is closed.')

@app.route('/estatisticas', methods=['GET'])
def estatisticas():
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    conn = None
    try:
        params = getDBConfigs()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        username = l['user']

        #verificar se o user e admin
        cur.execute('select pessoa.admin from pessoa where username = %s', (username, ))
        admin = cur.fetchall()[0][0]

        if not admin:
            message = {"code": 403, "message": "You don't have permission to access the data."}
            return jsonify(message)

        cur.execute("select leilao.pessoa_userid from leilao group by leilao.pessoa_userid order by count(leilao.pessoa_userid) desc")
        top_created_l = cur.fetchall()

        cur.execute("select licitacao.pessoa_userid from licitacao group by licitacao.pessoa_userid order by count(licitacao.pessoa_userid) desc")
        top_won_l = cur.fetchall()

        time_delta = datetime.timedelta(days = 10)
        current_date_minus_10 = (datetime.datetime.now() - time_delta).strftime("%Y-%m-%d %H:%M")
        cur.execute("select count(leilao.leilaoid) from leilao where datainicio > %s", (current_date_minus_10,))
        number_l = cur.fetchall()[0][0]

        lista = []

        temp = []
        for i in range(min(10, len(top_created_l))):
            temp.append(top_created_l[i][0])
        lista.append({"Top auction creaters": temp})

        temp = []
        for i in range(min(10, len(top_won_l))):
            temp.append(top_won_l[i][0])
        lista.append({"Top auction winners": temp})

        lista.append({"auctions created": number_l})

        return jsonify(lista)
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn:
            conn.close()
            print('Database connection is closed.')


@app.route('/cancelAuction/<leilaoId>', methods=['GET'])
def cancelarLeilao(leilaoId):
    l, code = token_required(request.args.get('token'))
    if code == 403:
        return l
    conn = None
    try:
        params = getDBConfigs()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        username = l['user']

        #verificar se o user e admin
        cur.execute('select pessoa.admin from pessoa where username = %s', (username, ))
        admin = cur.fetchall()[0][0]

        if not admin:
            message = {"code": 403, "message": "You don't have permission to access the data."}
            return jsonify(message)

        #verificar se o leilao ja acabou
        cur.execute("select datafim, cancelado from leilao where leilaoid = %s" , (leilaoId, ))
        data = cur.fetchall()
        datafim = data[0][0]
        status = data[0][1]

        if datafim < datetime.datetime.now() or status:#ja acabou
            return jsonify({"message": "Auction has ended already."})

        cur.execute("begin")
        cur.execute("update leilao set cancelado = true where leilao.leilaoid = %s", (leilaoId, ))
        cur.execute("commit")
        #Para a notificacao um trigger tem de ser criado par este update no registo do leilao
        return jsonify({"message": "Auction canceled."})
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn:
            conn.close()
            print('Database connection is closed.')
# TODO termino na hora(triggers ainda n demos), e partes do admin

if __name__ == '__main__':
    app.run(debug=True)
