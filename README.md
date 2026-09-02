# SisGeRec — Sistema de Gestão de Recursos (ComDivRib)

Painel logístico para controlar recursos (por ND/Origem), demandas, autorização do CEM
e acompanhamento do processo de aquisição, conforme o desenho aprovado.

Stack: FastAPI + SQLAlchemy + TiDB Cloud (MySQL-compatible) + Render (mesma stack zero-custo
usada no SisLog Mil e no QSVO).

## 1. Banco de dados (TiDB Cloud)

1. Crie (ou reaproveite) um cluster gratuito no TiDB Cloud (https://tidbcloud.com).
2. Crie um banco chamado `sisgerec`.
3. Copie a string de conexão no formato:
   `mysql+pymysql://USUARIO:SENHA@HOST:4000/sisgerec?ssl_verify_cert=true&ssl_verify_identity=true`
4. As tabelas são criadas automaticamente no primeiro start da aplicação (não é necessário rodar
   migração manual).

## 2. Deploy no Render

1. Suba esta pasta para um repositório no GitHub (pode ser privado).
2. No Render, crie um novo **Web Service** apontando para o repositório
   (o `render.yaml` já define build/start commands automaticamente).
3. Configure as variáveis de ambiente (aba *Environment*):
   - `DATABASE_URL` — a string de conexão do TiDB Cloud (passo 1)
   - `SECRET_KEY` — pode deixar o Render gerar automaticamente
   - `SUPERADMIN_NIP`, `SUPERADMIN_SENHA`, `SUPERADMIN_POSTO`, `SUPERADMIN_NOME`, `SUPERADMIN_SETOR`
     — dados do seu primeiro acesso como SUPERADMIN (só são usados uma vez, quando o banco
     ainda está vazio)
4. Faça o deploy. Acesse a URL gerada pelo Render e entre com o NIP/senha do SUPERADMIN.

## 3. Manter o serviço "acordado" (plano gratuito do Render)

Assim como no SisLog Mil e no QSVO, configure um ping periódico em https://cron-job.org
apontando para a URL do serviço (ex: a cada 10 minutos) para evitar que o plano gratuito
do Render suspenda a aplicação por inatividade.

## 4. Primeiro uso

1. Entre como SUPERADMIN.
2. Cadastre as **Origens** de recurso (menu Origens).
3. Lance os **Recursos** iniciais (ND + Origem + Valor).
4. Cadastre os demais usuários (ADMIN, CEM, usuários COMUM) em Admin > Usuários —
   uma senha provisória é gerada e exibida na tela para você repassar ao militar.
5. Em **Config. de Status**, cadastre a sequência de status de cada tipo de processo
   (Já licitado / Adesão / Dispensa de licitação / Cartão de suprimento de fundos)
   assim que sua equipe fechar essas listas. Enquanto isso não for feito, as parcelas
   autorizadas ficam paradas em "AUTORIZADA" até que o ADMIN/SUPERADMIN defina o tipo
   de processo de cada uma no painel de Status.

## 5. Rodar localmente (opcional, para testes)

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
Sem `DATABASE_URL` definida, a aplicação usa automaticamente um arquivo SQLite local
(`sisgerec_local.db`), útil apenas para testes — não use isso em produção.

## 6. Observação sobre este pacote

O código foi revisado e sua sintaxe foi validada (compilação Python de todos os módulos),
mas não pôde ser executado ponta a ponta neste ambiente por falta de acesso à rede para
instalar as dependências. Recomendo testar o fluxo completo (login → recurso → demanda →
autorização CEM → status) logo após o primeiro deploy, e me avisar se algo não se comportar
como esperado para eu corrigir.
