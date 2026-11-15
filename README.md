# media-controller

Controle remoto de mídia para Windows pelo celular, via navegador.

Um servidor em Python roda no PC e serve uma página web acessada pelo celular na mesma rede Wi-Fi. Não é necessário instalar nenhum aplicativo no celular.

O projeto não depende de um player específico. Ele usa recursos nativos do Windows (volume do sistema, mixer por aplicativo e os controles de mídia do sistema, os mesmos exibidos ao pressionar as teclas de volume), então funciona com YouTube no navegador, Spotify e qualquer outro player que se integre a esses controles.

## Funcionalidades

- Volume do sistema e mudo
- Volume individual por aplicativo, pelo slider ou em passos de 5
- Play/pause
- Avançar e voltar 10 segundos
- Tela cheia no YouTube e no Stremio
- Controles na tela de bloqueio do celular
- Seleção da mídia a controlar quando há mais de uma ativa

O Stremio é uma exceção: como não aparece nos controles de mídia do Windows, os comandos são enviados como teclas diretamente para a janela dele (espaço e setas).

## Instalação e uso

Requisitos: Windows e Python 3.12 (outras versões recentes devem funcionar).

```
start.bat
```

Na primeira execução, o script cria o `.venv` e instala as dependências. Em seguida, o terminal exibe um QR code com o endereço de acesso.

O endereço inclui um token que impede que outros dispositivos da rede controlem o PC. O token e a porta (8765 por padrão) ficam em `config.json`, gerado automaticamente e ignorado pelo git.

Para encerrar, feche a janela do terminal ou execute `stop.bat`.

### Firewall

Caso o celular não consiga acessar a página, libere a porta no firewall (PowerShell como administrador, apenas uma vez):

```
netsh advfirewall firewall add rule name="Media Controller" dir=in action=allow protocol=TCP localport=8765 profile=private
```

A rede Wi-Fi precisa estar configurada como Privada no Windows.

### Iniciar com o Windows

Pressione `Win+R`, abra `shell:startup` e crie um atalho para o `start.bat`. Para rodar sem janela, aponte o atalho para `.venv\Scripts\pythonw.exe server.py`, com "Iniciar em" definido para a pasta do projeto.

No celular, a opção "Adicionar à tela inicial" do navegador permite abrir a página em tela cheia, como um aplicativo.

### Tela de bloqueio

Ative a opção "Controles na tela de bloqueio" no final da página. A página passa a reproduzir um áudio inaudível em loop, o que faz o celular exibir o player na tela de bloqueio e na central de notificações, com play/pause, ±10s e as informações da mídia em reprodução no PC. Os botões de faixa anterior e próxima diminuem e aumentam o volume do sistema em 5.

Como a página reproduz áudio, ela pode interromper músicas tocando no próprio celular.

### Tela cheia

O botão de tela cheia aparece no card de mídia quando a ação está disponível. Ele traz a janela para frente no PC e envia a tecla `F`, atalho de tela cheia do YouTube e do Stremio. No YouTube, a aba do vídeo precisa ser a aba ativa da janela do navegador.

## Observações

- A janela do Stremio precisa estar aberta (pode ficar atrás de outras janelas, mas não minimizada).
- Se o controle do Stremio deixar de funcionar, defina `set MC_STREMIO_INPUT=focus` antes de executar o `start.bat`. Nesse modo a janela é trazida para frente por um instante, o que deixa os comandos um pouco mais lentos.
