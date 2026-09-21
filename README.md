# Elo Lorcana Portugal

Ranking Elo de jogadores de Disney Lorcana em Portugal, inspirado no EloShowdown (Riftbound).

## Âmbito

- Só eventos em lojas de **Portugal**.
- Só a era **pós-rotação**: desde **2025-09-05**, data de lançamento do Set 9 (Fabled), que iniciou a rotação.
- Só formato **Core Constructed** por omissão (muda com `--formats`). Draft, sealed e outros formatos de boosters não entram no Elo.

## Como funciona (tudo no GitHub, sem correres nada no teu computador)

O GitHub Actions corre todas as noites: recolhe os resultados do Ravensburger Play Hub, calcula o Elo e publica a página no GitHub Pages.

1. Cria uma conta em github.com e um repositório **público** (ex.: `lorcana-pt-elo`). O Pages gratuito exige repositório público. Os dados dos jogadores não ficam no repositório, só na página publicada.
2. Descompacta este zip e carrega os ficheiros: **Add file → Upload files**. Confirma que a pasta `.github/workflows/` ficou lá com os dois ficheiros `.yml`. Se o teu sistema esconde pastas com ponto, cria cada ficheiro com **Add file → Create new file**, escrevendo o caminho completo (`.github/workflows/update.yml`) e colando o conteúdo.
3. **Settings → Pages → Source: GitHub Actions**.
4. **Actions → "Descobrir a API do Play Hub" → Run workflow.** Quando acabar, abre a execução, copia o texto do passo "Sondar a API" e cola-o na conversa. Serve para confirmar os caminhos e nomes de campos da API antes de publicares dados reais.
5. Depois de ajustado: **Actions → "Atualizar ranking" → Run workflow.** O endereço da página aparece no passo "deploy".
6. Opcional: **Settings → Secrets and variables → Actions → Variables**, cria `CONTACT_EMAIL` com o email para pedidos de remoção.

## Estado da integração

Escrita a partir de fontes públicas sobre a API. Os endpoints "TV" estão confirmados; os caminhos de eventos, rondas e partidas e os nomes dos campos são os mais prováveis mas **ainda não foram testados contra a API real**. Os testes usam um servidor simulado, por isso provam a mecânica (paginação, filtros, cache, CSV) e não a forma real dos dados. O passo 4 serve para fechar isto.

O Play Hub bloqueia pedidos de browsers de outros sites (CORS), por isso a recolha corre no servidor do GitHub e a página final só mostra dados já calculados.

## Ficheiros

| Ficheiro | Para quê |
|---|---|
| `ingest_playhub.py` | Recolhe eventos de Portugal, rondas e partidas do Play Hub e escreve o CSV. `--probe` mostra a forma dos dados |
| `import_matches.py` | Importa o CSV para SQLite (idempotente, ignora byes, filtra datas) |
| `elo.py` | Motor de Elo: início 1000, K=40 nas primeiras 10 partidas e depois K=24, empate = 0,5, rondas calculadas com o rating de antes da ronda |
| `build_web.py` | Gera a página única (`index.html`) com ranking, jogadores, eventos e sobre |
| `build_site.py` | Alternativa: site em várias páginas |
| `make_sample_data.py` | Dados inventados para experimentar |
| `.github/workflows/` | `probe.yml` (descoberta) e `update.yml` (atualização noturna e publicação) |

## Formato do CSV entre a recolha e o importador

```
event_id,event_name,event_date,store,city,round,player_a_id,player_a_name,player_b_id,player_b_name,result
```

`result` é `A`, `B` ou `D` (empate). Sem `player_b_id` é bye. O `player_*_id` deve ser o id estável do jogador, não o nome.

## Experimentar localmente (opcional)

```bash
python make_sample_data.py
python import_matches.py data/sample_matches.csv --db data/demo.db
python build_web.py --db data/demo.db --out web/index.html --demo
python -m unittest
```

## Privacidade

O nome mostrado é o nome de utilizador do Play Hub; se não existir, primeiro nome e inicial do apelido, nunca o nome completo.
Para omitir alguém, põe o id do jogador em `opt_out.txt` (um por linha): a página desaparece e o nome passa a "Jogador anónimo" nas listas dos adversários.
