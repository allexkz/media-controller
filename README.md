# media-controller

Controle remoto de mídia para Windows pelo celular, via navegador.

Um servidor em Python roda no PC e serve uma página web que abre no celular, na mesma rede Wi-Fi. Não precisa instalar app no celular.

Não depende de nenhum player específico. Usa o que o próprio Windows já oferece (o volume do sistema, o mixer por aplicativo e os controles de mídia que aparecem quando você aperta as teclas de volume), então funciona com YouTube no navegador, Spotify e qualquer coisa que apareça ali.

## O que dá pra fazer

- volume geral e mudo
- volume de cada app separado
- play/pause
- avançar e voltar 10s
- escolher qual mídia controlar quando tem mais de uma tocando

O Stremio é uma exceção: ele não aparece nos controles de mídia do Windows, então as teclas são enviadas direto pra janela dele (espaço e setas).

## Como usar

Precisa de Windows e Python 3.12 (outras versões recentes devem funcionar).

```
start.bat
```

Na primeira vez ele cria o `.venv` e instala as dependências. Depois aparece um QR code no terminal, é só ler com o celular.

O link tem um token pra ninguém da rede sair mexendo no seu volume. Esse token e a porta (8765 por padrão) ficam no `config.json`, que é criado sozinho e não vai pro git.

Pra parar, fecha a janela ou roda `stop.bat`.

### Firewall

Se o celular não conseguir abrir a página, libera a porta (PowerShell como admin, só uma vez):

```
netsh advfirewall firewall add rule name="Media Controller" dir=in action=allow protocol=TCP localport=8765 profile=private
```

A rede Wi-Fi tem que estar como Privada no Windows.

### Iniciar junto com o Windows

`Win+R`, digita `shell:startup` e cria um atalho pro `start.bat`. Se preferir sem janela, aponta o atalho pra `.venv\Scripts\pythonw.exe server.py` com "Iniciar em" nessa pasta.

No celular dá pra usar "Adicionar à tela inicial", aí abre em tela cheia como se fosse um app.

## Observações

- A janela do Stremio precisa estar aberta (pode estar atrás de outras, só não minimizada).
- Se o controle do Stremio parar de funcionar, rode `set MC_STREMIO_INPUT=focus` antes do `start.bat`. Fica um pouco mais lento porque a janela vem pra frente rapidinho.
