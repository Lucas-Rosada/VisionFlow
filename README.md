# IAMouse - controle pela posicao das iris

Move o cursor real do PC usando a posicao de cada iris em relacao aos cantos do olho. As palpebras servem para identificar olhos fechados, sem cancelar o movimento vertical da iris. A camera fica em janela normal com contornos verdes, iris amarelas, ampliacao dos olhos e indicador da direcao.

O controle agora e direcional: olhar a direita move o cursor para a direita; olhar acima move para cima. Voltar ao olhar central para o movimento. Nao posiciona o cursor exatamente sobre o objeto observado.

## Executar

```powershell
.\.venv\Scripts\python.exe mouse_olhos.py
```

1. Olhe para o centro do monitor e pressione **Espaco**. Mantenha o olhar por tres segundos para registrar sua posicao neutra. Nao ha mais nove pontos.
2. **F8** ativa ou pausa o movimento do cursor real do PC.
3. Mova os olhos para os lados, para cima ou para baixo. Volte ao centro para parar.
4. **F9** registra novamente o centro; **Esc** encerra. No Windows esses atalhos funcionam fora da janela. **P/C/Q** tambem pausam/calibram/encerram com a janela em foco.

Para aumentar a resposta:

```powershell
.\.venv\Scripts\python.exe mouse_olhos.py --sensibilidade 1.5
```

Use `--sensibilidade 0.7` para diminuir a resposta, ou `--camera 1` para outra webcam. Cliques continuam no mouse fisico. O cursor para ao fechar os olhos ou perder a deteccao. Ctrl+C no terminal encerra. A protecao de cantos do PyAutoGUI permanece ativa.

## Precisao

Confira na ampliacao se os pontos amarelos acompanham as iris. Ilumine o rosto pela frente, evite contraluz e mantenha a postura estavel. A normalizacao reduz o efeito de deslocamento e distancia do rosto, mas nao compensa toda rotacao da cabeca. Recalibre com F9 ao mudar de postura. Webcam comum tem precisao limitada.

O programa usa o monitor principal, processa imagens localmente e nao salva nem envia video. O modelo do MediaPipe e baixado na primeira execucao. A calibracao dura apenas a sessao.

## Instalar novamente e verificar a sintaxe

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m py_compile gaze.py mouse_olhos.py
```

A verificacao acima confere a sintaxe do codigo. A precisao real exige testar com sua webcam.
