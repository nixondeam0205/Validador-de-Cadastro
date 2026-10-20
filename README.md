# Validador de Cadastro — 2.5.7

Aplicativo desktop Tkinter para gerar validações Amazon e MELI com base nos relatórios BRK importados pelo usuário.

## Recursos

- Importa relatórios de motorista e veículo em `.xlsx` e mantém os dados somente na memória.
- Identifica CPFs, nomes e placas colados no campo de texto e permite ajustar os papéis das placas.
- Consulta resultados nos relatórios locais, sem Selenium ou acesso ao site da BRK.
- Mantém os campos de status, validade, Frota Legal, LWEB, atalhos F1–F4 e prévia da validação.
- Permite redimensionar e rolar a interface em telas menores.

## Executar pelo código

```powershell
python -m pip install -r requirements.txt
python app.py
```

## Gerar executável

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name ValidadorCadastro --add-data "losung.png;." app.py
```

O `app_old.py` é mantido no repositório como a versão anterior. A versão distribuída é `ValidadorCadastro_v2.5.7.exe` na release `v2.5.7`.
