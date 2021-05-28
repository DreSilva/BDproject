create or replace procedure banUserProc(userid pessoa.userid%type)
language plpgsql
as $$
declare
    c5 cursor for
    select leilaoid from leilao where leilao.pessoa_userid = userid and leilao.cancelado = false;
    c6 cursor for
    select distinct licitacao.leilao_leilaoid from licitacao where licitacao.pessoa_userid = userid;
    min_value licitacao.valor%type;
    min_licitacao_id licitacao.licitacaoid%type;
    max_licitacao_id licitacao.licitacaoid%type;
    userT licitacao.pessoa_userid%type;

begin
    for elem in c5
    loop
        --cancelar os leiloes criados pelo user
        --vai chamar o trigger que manda notificacao e invalida as licitacoes no leilao
        update leilao set cancelado = true where leilao.leilaoid = elem.leilaoid;
    end loop;

    --percorrer os leiloes em que o user banido licitou
    for elem in c6
    loop
        --obter o id e o valor da licitacao mais baixa do user que esta a ser banido
        select licitacao.licitacaoid, licitacao.valor into min_licitacao_id, min_value from licitacao where licitacao.leilao_leilaoid = elem.leilao_leilaoid and licitacao.valor = (select min(licitacao.valor) from licitacao where licitacao.pessoa_userid = userid and licitacao.leilao_leilaoid = elem.leilao_leilaoid);
        --obter o id da licitacao mais alta no leilao que nao seja do user a ser banido
        select licitacao.licitacaoid into max_licitacao_id from licitacao where licitacao.leilao_leilaoid = elem.leilao_leilaoid and licitacao.valor = (select max(licitacao.valor) from licitacao where licitacao.leilao_leilaoid = elem.leilao_leilaoid and licitacao.pessoa_userid <> userid );
        --atualizar o valor da licitacao mais alta que nao e do user para o valor da licitacao mais baixa do user no leilao
        update licitacao set valor = min_value where licitacaoid = max_licitacao_id;
        --colocar todas as licitacoes mais altas que a nova melhor e a do user que tinha o min_value como invalidas
        update licitacao set valida = false where licitacao.leilao_leilaoid = elem.leilao_leilaoid and licitacao.valor > min_value or licitacao.licitacaoid = min_licitacao_id;
    
        --enviar a notificacao para todos os interessados no leilao
        for userT in (select distinct licitacao.pessoa_userid from licitacao where licitacao.leilao_leilaoid = elem.leilao_leilaoid)
        loop
            insert into notificacao (pessoa_userid, mensagem) values(userT, 'A user has been banned, so the bids have been updated on the auction number ' || elem.leilao_leilaoid || '. The hihgest value is ' || min_value || '.');
        end loop;

        --escrever mensagem no mural do leilao
        insert into comentario (comentario, leilao_leilaoid, pessoa_userid) values ('The user with id ' || userid || ' was banned. The bids have been updated. We''re sorry for the inconvenience.', elem.leilao_leilaoid, userid);
    end loop;

end;
$$;


create or replace function banUserFunc() returns trigger
language plpgsql
as $$
begin
    call banUserProc(old.userid);
    return new;
end;
$$;

create trigger banUserTrig before update of banned on pessoa for each row execute procedure banUserFunc();