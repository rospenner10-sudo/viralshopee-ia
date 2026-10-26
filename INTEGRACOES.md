# Mapa de integrações — ViralShopee IA 2.0

| Recurso | Estado atual | O que falta |
|---|---|---|
| Painel web | Implementado localmente | Hospedagem, autenticação e HTTPS para acesso remoto |
| Meta de 10 vídeos/dia | Configuração implementada | Agendador e fila de tarefas em ambiente hospedado |
| Busca de produtos | Demo + adaptador de feed JSON | URL e credenciais de fonte autorizada de dados de afiliado/Shopee |
| Links de afiliada | Campo disponível | Inserir/obter links por integração autorizada; validar regras do programa |
| MP4 vertical | Renderização local real, sem áudio | FFmpeg + Pillow; imagem opcional. Para vídeos com movimento real, integrar gerador externo |
| Apresentadora virtual | Não conectada | Serviço de vídeo/voz (ex.: Higgsfield, Runway ou equivalente), conta e créditos |
| Narração/legendas faladas | Roteiro textual disponível | TTS externo ou motor local; revisão da pronúncia e direitos de voz |
| Revisão humana | Implementada | Aprovação interna; ainda não publica em nenhuma plataforma |
| Publicação | Não implementada | APIs oficiais, autorização, tokens e cumprimento das políticas das plataformas |
| Cliques e vendas | Não integrados | Analytics/relatórios de afiliado autorizados |

Não coloque senhas pessoais ou tokens sensíveis num ambiente compartilhado. A configuração atual é local e não tem cofre de segredos.
| Narração básica | Tentativa local via espeak `pt-br` quando instalado | Qualidade limitada; voz natural exige TTS externo |
| Geração em lote | Botão para gerar até a meta configurada | Agendador diário persistente requer hospedagem e worker |
