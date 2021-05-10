create or replace procedure sendCancelNotificationProc(leilaoId licitacao.leilao_leilaoid%type)
language plpgsql
as $$
declare
    c1 cursor for
    select DISTINCT licitacao.pessoa_userid from licitacao where licitacao.leilao_leilaoid = leilaoId;
begin
    for elem in c1
    loop
        insert into notificacao (pessoa_userid, mensagem) values(elem.pessoa_userid, 'The auction number ' || leilaoId || ' has been canceled by an admin.');
    end loop;

end;
$$;


create or replace function sendCancelNotificationFunc() returns trigger
language plpgsql
as $$
begin
    call sendCancelNotificationProc(old.leilaoid);
    return new;
end;
$$;

create trigger sendCancelNotificationTrig before update of cancelado on leilao for each row execute procedure sendCancelNotificationFunc();