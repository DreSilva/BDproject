create or replace procedure banUserProc(userid pessoa.userid%type)
language plpgsql
as $$
declare
    c5 cursor for
    select leilaoid from leilao where leilao.pessoa_userid = userid;
    c6 cursor for
    select licitacaoid from licitacao where licitacao.pessoa_userid = userid;
begin
    for elem in c5
    loop
        update leilao set cancelado = true where leilao.leilaoid = elem.leilaoid;
    end loop;
    for elem in c6
    loop
        update licitacao set valida = false where licitacao.licitacaoid = elem.licitacaoid;
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