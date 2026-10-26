# Publicação no Render (apenas guia; revisar antes de publicar)

1. O servidor agora escuta em `0.0.0.0` na porta `PORT` fornecida pelo Render.
2. A autenticação HTTP Basic é obrigatória: defina variáveis de ambiente `APP_USERNAME` e `APP_PASSWORD` no Render antes de iniciar o serviço.
3. Build command: `apt-get update && apt-get install -y ffmpeg espeak && pip install -r requirements.txt`
4. Start command: `python server.py`
5. Não coloque tokens no GitHub. Configure feeds e tokens apenas depois de autenticação ativa.

IMPORTANTE: o armazenamento de `data.json`, `config.json` e `output/` continua sendo local ao contêiner. Em serviços sem disco persistente, arquivos podem desaparecer em deploys/reinicializações. Não usar para dados importantes até configurar persistent disk ou armazenamento externo. O feed de produtos Shopee e a geração com apresentadora virtual não estão conectados por este deploy.
