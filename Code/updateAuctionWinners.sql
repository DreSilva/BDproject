create or replace procedure updateAuctionWinners()
--atualiza os vencedores dos leiloes que tenham acabado e ainda nao tenham associado um vencedor
language plpgsql
as $$
declare
    --cursor com os ids dos leiloes que ainda nao tem vencedor e ja acabaram
    c1 cursor for
    select distinct licitacao.leilao_leilaoid from licitacao, leilao where licitacao.leilao_leilaoid = leilao.leilaoid and leilao.datafim < current_timestamp(0) and leilao.vencedor is null;
    winner leilao.vencedor%type;
begin
    for elem in c1
    loop
        --obter o vencedor do leilao
        select licitacao.pessoa_userid into winner from licitacao where licitacao.leilao_leilaoid = elem.leilao_leilaoid and licitacao.valida = true and licitacao.valor = (select max(licitacao.valor) from licitacao where licitacao.leilao_leilaoid = elem.leilao_leilaoid and licitacao.valida = true);
        --associar vencedor ao leilao
        update leilao set vencedor = winner, terminado = true where leilao.leilaoid = elem.leilao_leilaoid;
    end loop;
end;
$$;