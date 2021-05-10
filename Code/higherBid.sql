create or replace procedure sendHigherBidNotificationProc(leilaoId licitacao.leilao_leilaoid%type, value licitacao.valor%type, userId licitacao.pessoa_userid%type)
language plpgsql
as $$
declare
    c1 cursor for
    select distinct pessoa_userid from licitacao where leilao_leilaoid = leilaoId and pessoa_userid <> userId;
begin
    for elem in c1
    loop
        insert into notificacao (pessoa_userid, mensagem) values(elem.pessoa_userid, 'There''s been a better bid on the auction number ' || leilaoId || ' , with value ' || value || '.');
    end loop;

end;
$$;


create or replace function sendHigherBidNotificationFunc() returns trigger
language plpgsql
as $$
begin
    call sendHigherBidNotificationProc(new.leilao_leilaoid, new.valor, new.pessoa_userid);
    return new;
end;
$$;

create trigger sendHigherBidNotificationTrig before insert on licitacao for each row execute procedure sendHigherBidNotificationFunc();