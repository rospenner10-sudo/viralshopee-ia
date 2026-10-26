# ViralShopee IA 2.0 — protótipo local funcional

## O que funciona nesta versão
- Painel responsivo para celular/computador.
- Meta configurada para 10 vídeos/dia (a meta é uma configuração, não um agendador automático).
- Produtos de demonstração explicitamente identificados como fictícios; cadastro manual; tentativa de consulta de feed JSON HTTPS autorizado.
- Geração local de MP4 vertical 720x1280 com cenas gráficas, texto e preço, usando FFmpeg + Pillow.
- Roteiro, legenda com divulgação de afiliado, fila de revisão humana, aprovar/rejeitar e exportação de backup JSON.
- Dados e configurações salvos em `data.json` e `config.json` na primeira execução.

## Requisitos
- Python 3.10+
- FFmpeg instalado e acessível no PATH
- Pillow: `python -m pip install -r requirements.txt`
- Opcional: `espeak` para futuras extensões de narração. Nesta versão, o MP4 é renderizado sem áudio.

## Como iniciar
1. Descompacte o ZIP numa pasta do computador.
2. Instale Pillow: `python -m pip install -r requirements.txt`
3. Execute `python server.py`.
4. Abra `http://127.0.0.1:8765` no navegador.
5. Para encerrar, pressione Ctrl+C no terminal.

No Windows, instale o FFmpeg e adicione-o ao PATH antes de iniciar. O app não deve ser publicado na internet sem autenticação, HTTPS, gestão de segredos e revisão de segurança.

## Conectar dados reais de produtos
Em Configurações, informe a URL HTTPS de um endpoint/feed JSON ao qual você tenha acesso autorizado. Pode ser uma integração própria ou um feed que o programa de afiliados disponibilize para sua conta. Opcionalmente, informe token Bearer. Formatos aceitos:

`[{"id":"123","name":"Produto","price":"29,90","category":"Casa","rating":"4.8","sales":"500","commission":"5%","affiliate_url":"https://...","image_url":"https://...","benefits":["Benefício 1","Benefício 2"]}]`

ou `{ "products": [ ... ] }`.

O protótipo não tem credenciais de afiliada nem integração oficial Shopee embutida. Sem feed configurado, “Buscar produtos” apenas mostra os exemplos demonstrativos. Preços, avaliações, estoque e comissão não são confirmados em tempo real.

## Limitações e próximos passos
- O MP4 atual é um vídeo de cartões/cenas gráficas. Se houver URL pública de imagem, ela é usada; sem imagem, aparece um marcador indicando que a foto não foi fornecida.
- Sem narração/áudio nesta versão.
- O estilo “apresentadora virtual” ainda não é gerado aqui: precisa de serviço externo de vídeo/voz e credenciais/créditos.
- O painel ainda não agenda 10 gerações automaticamente. A meta de 10 é registrada, mas as gerações são iniciadas manualmente para evitar custos inesperados.
- Não publica em Shopee, TikTok, Instagram ou YouTube. Aprovação é apenas uma etapa interna; publicação exigiria APIs oficiais, autorização e permissões das plataformas.
- Para produção: backend hospedado, autenticação, criptografia de tokens, fila de tarefas, agendador, logs, armazenamento de mídia, limites de custo, testes de segurança e integração de analytics/cliques/conversões.

### Geração em lote
O botão **Gerar até 10 vídeos** gera vídeos para os produtos disponíveis e coloca todos em revisão. Isso é uma execução em lote manual, não um agendador diário persistente; para executar todo dia automaticamente, a próxima etapa é hospedar o backend e adicionar um agendador/fila de tarefas.

Se `espeak` com voz `pt-br` estiver instalado, o renderizador tenta adicionar narração sintetizada localmente. A voz é robótica e precisa ser revisada; para uma voz natural/apresentadora virtual, conecte um serviço externo.
