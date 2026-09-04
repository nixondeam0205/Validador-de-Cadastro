import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import sys
import requests


VERSAO_ATUAL = "1.4.5"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def verificar_atualizacao():

    try:

        resposta = requests.get(
            "https://raw.githubusercontent.com/nixondeam0205/Validador-de-Cadastro/main/version.json",
            timeout=5
        )

        dados = resposta.json()

        versao_nova = dados["versao"]

        if versao_nova != VERSAO_ATUAL:

            baixar = messagebox.askyesno(
                "Atualização disponível",
                f"Sua versão: {VERSAO_ATUAL}\n\n"
                f"Nova versão: {versao_nova}\n\n"
                "Deseja baixar agora?"
            )

            if baixar:

                pasta_downloads = os.path.join(
                    os.path.expanduser("~"),
                    "Downloads"
                )

                caminho_arquivo = os.path.join(
                    pasta_downloads,
                    f"ValidadorCadastro_v{versao_nova}.exe"
                )

                download = requests.get(
                    dados["download"],
                    stream=True
                )

                with open(caminho_arquivo, "wb") as arquivo:

                    for bloco in download.iter_content(
                        chunk_size=8192
                    ):

                        if bloco:
                            arquivo.write(bloco)

                messagebox.showinfo(
                    "Download concluído",
                    f"Arquivo salvo em:\n\n{caminho_arquivo}\n\n"
                    "Feche esta versão e execute a nova."
                )

    except Exception as erro:

        print(
            f"Erro ao verificar atualização: {erro}"
        )

def converter_status(valor):

    mapa = {
    "OK": "✅ OK",
    "Renovar": "⚠️ Renovar",
    "Em análise": "⚠️ Em análise",
    "Inapto": "❌ Inapto",
    "Vencido": "⚠️ Vencido",
    "Sem checklist": "❌ Sem checklist",
    "Reprovado": "❌ Reprovado",
    "Cadastro": "✅ Cadastro",
    "Validar": "⚠️ Validar",
    "Atualizar cadastro": "⚠️ Atualizar cadastro",
    "Sem cadastro": "❌ Sem cadastro"
}

    return mapa.get(valor, valor)

def gerar_validacao():

    campos_obrigatorios = [
        brk_var.get(),
        onboarding_var.get(),
        et_var.get(),
        tdd_var.get(),
        checklist_var.get(),
        cavalo_brk_var.get(),
        fl_checklist_var.get(),
        lweb_motorista_var.get(),
        lweb_cavalo_var.get()
    ]

    if possui_carreta_var.get():
        campos_obrigatorios.extend([
            carreta_brk_var.get(),
            lweb_carreta_var.get()
        ])

    if (
    "(SELECIONE)" in campos_obrigatorios
    ):
        messagebox.showerror(
            "Erro",
            "Existem campos não preenchidos."
        )
        return

    motorista1 = motorista1_entry.get().strip()
    motorista2 = motorista2_entry.get().strip()
    cpf1 = cpf1_entry.get().strip()
    cpf2 = cpf2_entry.get().strip()

    cavalo = cavalo_entry.get().strip().upper()
    carreta = carreta_entry.get().strip().upper()
    ano_cavalo = ano_cavalo_entry.get().strip()

    status_ano = ""

    ano_minimo = int(ano_minimo_var.get())

    if ano_cavalo.isdigit():
        if int(ano_cavalo) < ano_minimo:
            status_ano = " ❌ INAPTO"

    ano_apto = (
    ano_cavalo.isdigit()
    and int(ano_cavalo) >= ano_minimo
)

    tem_carreta = possui_carreta_var.get()

    status_carreta = ""
    lweb_carreta = ""

    if tem_carreta:

        status_carreta = (
            f"\nPlaca Carreta BRK: "
            f"{converter_status(carreta_brk_var.get())}"
        )

        lweb_carreta = (
            f"\nCarreta: "
            f"{converter_status(lweb_carreta_var.get())}"
        )

    if motorista2:
        motorista_texto = (
            f"👤 Motoristas:\n"
            f"{motorista1} | CPF: {cpf1}\n"
            f"{motorista2} | CPF: {cpf2}"
        )
    else:
        motorista_texto = (
           f"👤 Motorista:\n"
           f"{motorista1} | CPF: {cpf1}"
        )

    if tem_carreta:
        placas = " / ".join(
        [p for p in [cavalo, carreta] if p]
    )
    else:
        placas = cavalo
    
    # STATUS

    status_ok = (
        brk_var.get() == "OK"
        and onboarding_var.get() == "OK"
        and et_var.get() == "OK"
        and tdd_var.get() == "OK"
        and checklist_var.get() == "OK"
        and cavalo_brk_var.get() == "OK"
        and ano_apto
        and (
            not tem_carreta
            or carreta_brk_var.get() == "OK"
        )
    )

    if status_ok:
        status_label.config(
            text="🟢 STATUS",
            fg="green"
        )

        status_titulo = "🟢 STATUS"

    else:
        status_label.config(
            text="🔴 STATUS",
            fg="red"
        )

        status_titulo = "🔴 STATUS"

# FROTA LEGAL

    frota_ok = (
        fl_checklist_var.get() == "OK"
    )

    if frota_ok:
        frota_label.config(
            text="🟢 FROTA LEGAL",
            fg="green"
        )

        frota_titulo = "🟢 FROTA LEGAL"

    else:
        frota_label.config(
            text="🔴 FROTA LEGAL",
            fg="red"
        )

        frota_titulo = "🔴 FROTA LEGAL"
    
    if (
        lweb_motorista_var.get() == "Cadastro"
        and lweb_cavalo_var.get() == "Cadastro"
        and (
        not tem_carreta
        or lweb_carreta_var.get() == "Cadastro"
        )
    ):
        lweb_label.config(
        text="🟢 LWEB",
        fg="green"
        )

        lweb_status = "🟢 LWEB"

    else:
        lweb_label.config(
        text="🔴 LWEB",
        fg="red"
        )

        lweb_status = "🔴 LWEB"

    texto = f"""🚛 VALIDAÇÃO DE CADASTRO

{motorista_texto}

🚛 Placas:
{placas}

━━━━━━━━━━━━━━━
{status_titulo}

BRK: {converter_status(brk_var.get())}
Onboarding: {converter_status(onboarding_var.get())}
ET: {converter_status(et_var.get())}
TDD: {converter_status(tdd_var.get())}
Checklist: {converter_status(checklist_var.get())}
Placa Cavalo BRK: {converter_status(cavalo_brk_var.get())}{status_carreta}
Ano do Cavalo: {ano_cavalo}{status_ano}

━━━━━━━━━━━━━━━
{frota_titulo}

Inspeção: {converter_status(fl_checklist_var.get())}

━━━━━━━━━━━━━━━
{lweb_status}

Motorista: {converter_status(lweb_motorista_var.get())}
Cavalo: {converter_status(lweb_cavalo_var.get())}{lweb_carreta}
"""

    if (
    lweb_motorista_var.get() == "Sem cadastro"
    ):

        texto += """

━━━━━━━━━━━━━━━
📄 DOCUMENTAÇÃO NECESSÁRIA

* CNH em PDF
* Comprovante de residência
* Certificado de Direção Defensiva (1 ano)
* CRLV
* ANTT
* Comprovante bancário do titular da ANTT
* Chave Pix do titular da ANTT

━━━━━━━━━━━━━━━
📲 CADASTRO

Nosso processo de cadastro é realizado 100% pelo próprio motorista, diretamente pelo aplicativo ou via navegador:

📲 Baixe o aplicativo:
https://play.google.com/store/apps/details?id=br.com.linehaul_driver&pcampaignid=web_share

━━━━━━━━━━━━━━━
📞 SUPORTE

WhatsApp: +55 85 98108-0605
Ligações: +55 85 99666-0104
"""

    preview_text.delete("1.0", tk.END)
    preview_text.insert("1.0", texto)

    janela.clipboard_clear()
    janela.clipboard_append(texto)
    janela.update()

def preencher_status_ok(event=None):

    brk_var.set("OK")
    onboarding_var.set("OK")
    et_var.set("OK")
    tdd_var.set("OK")
    checklist_var.set("OK")

    cavalo_brk_var.set("OK")

    if possui_carreta_var.get():
        carreta_brk_var.set("OK")


def preencher_frota_ok(event=None):

    fl_checklist_var.set("OK")


def preencher_lweb_ok(event=None):

    lweb_motorista_var.set("Cadastro")
    lweb_cavalo_var.set("Cadastro")

    if possui_carreta_var.get():
        lweb_carreta_var.set("Cadastro")

def limpar_campos():

    motorista1_entry.delete(0, tk.END)
    motorista2_entry.delete(0, tk.END)
    cpf1_entry.delete(0, tk.END)
    cpf2_entry.delete(0, tk.END)

    cavalo_entry.delete(0, tk.END)
    carreta_entry.delete(0, tk.END)
    ano_cavalo_entry.delete(0, tk.END)
    possui_carreta_var.set(True)

    brk_var.set("(SELECIONE)")
    onboarding_var.set("(SELECIONE)")
    et_var.set("(SELECIONE)")
    tdd_var.set("(SELECIONE)")
    checklist_var.set("(SELECIONE)")

    cavalo_brk_var.set("(SELECIONE)")
    carreta_brk_var.set("(SELECIONE)")

    fl_checklist_var.set("(SELECIONE)")

    lweb_motorista_var.set("(SELECIONE)")
    lweb_cavalo_var.set("(SELECIONE)")
    lweb_carreta_var.set("(SELECIONE)")

    status_label.config(
        text="🟢 STATUS",
        fg="green"
    )

    frota_label.config(
        text="🟢 FROTA LEGAL",
        fg="green"
    )

    lweb_label.config(
        text="🟢 LWEB",
        fg="green"
    )

    preview_text.delete("1.0", tk.END)


def formatar_placa(event):

    widget = event.widget

    texto = (
        widget.get()
        .upper()
        .replace("-", "")
        .replace(".", "")
        .replace(" ", "")
    )

    widget.delete(0, tk.END)
    widget.insert(0, texto)


def formatar_cpf(event):

    widget = event.widget

    numeros = "".join(
        c for c in widget.get()
        if c.isdigit()
    )[:11]

    cpf = numeros

    if len(numeros) > 3:
        cpf = numeros[:3] + "." + numeros[3:]

    if len(numeros) > 6:
        cpf = cpf[:7] + "." + cpf[7:]

    if len(numeros) > 9:
        cpf = cpf[:11] + "-" + cpf[11:]

    widget.delete(0, tk.END)
    widget.insert(0, cpf)

def formatar_nome(event):

    widget = event.widget

    texto = widget.get()

    palavras = texto.split()

    texto_formatado = " ".join(
        palavra.capitalize()
        for palavra in palavras
    )

    cursor = widget.index(tk.INSERT)

    widget.delete(0, tk.END)
    widget.insert(0, texto_formatado)

    widget.icursor(cursor)


janela = tk.Tk()

verificar_atualizacao()

janela.title("Validador de Cadastro")
janela.geometry("850x900")

logo_img = Image.open(
    resource_path("losung.png")
)

logo_img = logo_img.resize(
    (160, 55)
)

logo_tk = ImageTk.PhotoImage(logo_img)

creditos = tk.Label(
    janela,
    text="Desenvolvido por: Nixon Deam da Silva Cavalcanti | Versão: 1.4.5",
    font=("Arial", 8),
    fg="gray40"
)

creditos.pack(
    anchor="w",
    padx=10,
    pady=(5, 0)
)

logo_label = tk.Label(
    janela,
    image=logo_tk,
    borderwidth=0
)

logo_label.place(
    relx=1.0,
    x=-20,
    y=10,
    anchor="ne"
)

titulo = tk.Label(
    janela,
    text="🚛 VALIDADOR DE CADASTRO",
    font=("Arial", 16, "bold")
)

titulo.pack(pady=(10, 0))

atalhos_label = tk.Label(
    janela,
    text="⚡ F1 = STATUS OK    ⚡ F2 = FROTA OK    ⚡ F3 = LWEB OK",
    font=("Arial", 9, "bold"),
    fg="darkgreen"
)

atalhos_label.pack(pady=(0, 10))

frame = tk.Frame(janela)
frame.pack(pady=5)

# =========================
# DADOS
# =========================

tk.Label(frame, text="Motorista 1").grid(row=0, column=0, sticky="w")

motorista1_entry = tk.Entry(frame, width=30)
motorista1_entry.grid(row=0, column=1)

motorista1_entry.bind(
    "<FocusOut>",
    formatar_nome
)

tk.Label(frame, text="CPF").grid(row=0, column=2, padx=(10,0))

cpf1_entry = tk.Entry(frame, width=18)
cpf1_entry.grid(row=0, column=3)
cpf1_entry.bind("<KeyRelease>", formatar_cpf)

tk.Label(frame, text="Motorista 2").grid(row=1, column=0, sticky="w")

motorista2_entry = tk.Entry(frame, width=30)
motorista2_entry.grid(row=1, column=1)

motorista2_entry.bind(
    "<FocusOut>",
    formatar_nome
)

tk.Label(frame, text="CPF").grid(row=1, column=2, padx=(10,0))

cpf2_entry = tk.Entry(frame, width=18)
cpf2_entry.grid(row=1, column=3)
cpf2_entry.bind("<KeyRelease>", formatar_cpf)

tk.Label(frame, text="Placa Cavalo").grid(row=2, column=0, sticky="w")
cavalo_entry = tk.Entry(frame, width=40)
cavalo_entry.grid(row=2, column=1)
cavalo_entry.bind("<KeyRelease>", formatar_placa)

tk.Label(frame, text="Placa Carreta").grid(row=3, column=0, sticky="w")
carreta_entry = tk.Entry(frame, width=40)
carreta_entry.grid(row=3, column=1)
carreta_entry.bind("<KeyRelease>", formatar_placa)

possui_carreta_var = tk.BooleanVar(value=True)

chk_carreta = tk.Checkbutton(
    frame,
    text="Possui carreta",
    variable=possui_carreta_var
)

chk_carreta.grid(row=3, column=2, padx=10, sticky="w")

# =========================
# STATUS
# =========================

status_label = tk.Label(
    frame,
    text="🟢 STATUS",
    font=("Arial", 11, "bold"),
    fg="green",
    width=20,
    anchor="w"
)

status_label.grid(
    row=4,
    column=0,
    pady=10,
    sticky="w"
)

status_padrao = [
    "(SELECIONE)",
    "OK",
    "Renovar",
    "Inapto"
]

checklist_opcoes = [
    "(SELECIONE)",
    "OK",
    "Vencido",
    "Sem checklist",
    "Inapto",
    "Reprovado"
]

placa_opcoes = [
    "(SELECIONE)",
    "OK",
    "Renovar",
    "Em análise",
    "Inapto",
    "Sem cadastro"
]

# BRK

tk.Label(frame, text="BRK").grid(row=5, column=0, sticky="w")

brk_var = tk.StringVar(value="(SELECIONE)")

brk_opcoes = [
    "(SELECIONE)",
    "OK",
    "Renovar",
    "Em análise",
    "Inapto",
    "Sem cadastro"
]

ttk.Combobox(
    frame,
    textvariable=brk_var,
    values=brk_opcoes,
    state="readonly",
    width=25
).grid(row=5, column=1)

# Onboarding

tk.Label(frame, text="Onboarding").grid(row=6, column=0, sticky="w")

onboarding_var = tk.StringVar(value="(SELECIONE)")

ttk.Combobox(
    frame,
    textvariable=onboarding_var,
    values=status_padrao,
    state="readonly",
    width=25
).grid(row=6, column=1)

# ET

tk.Label(frame, text="ET").grid(row=7, column=0, sticky="w")

et_var = tk.StringVar(value="(SELECIONE)")

ttk.Combobox(
    frame,
    textvariable=et_var,
    values=status_padrao,
    state="readonly",
    width=25
).grid(row=7, column=1)

# TDD

tk.Label(frame, text="TDD").grid(row=8, column=0, sticky="w")

tdd_var = tk.StringVar(value="(SELECIONE)")

ttk.Combobox(
    frame,
    textvariable=tdd_var,
    values=status_padrao,
    state="readonly",
    width=25
).grid(row=8, column=1)

# Checklist

tk.Label(frame, text="Checklist").grid(row=9, column=0, sticky="w")

checklist_var = tk.StringVar(value="(SELECIONE)")

ttk.Combobox(
    frame,
    textvariable=checklist_var,
    values=checklist_opcoes,
    state="readonly",
    width=25
).grid(row=9, column=1)

# Cavalo BRK

tk.Label(frame, text="Placa Cavalo BRK").grid(row=10, column=0, sticky="w")

cavalo_brk_var = tk.StringVar(value="(SELECIONE)")

ttk.Combobox(
    frame,
    textvariable=cavalo_brk_var,
    values=placa_opcoes,
    state="readonly",
    width=25
).grid(row=10, column=1)

# Carreta BRK

tk.Label(frame, text="Placa Carreta BRK").grid(row=11, column=0, sticky="w")

carreta_brk_var = tk.StringVar(value="(SELECIONE)")

ttk.Combobox(
    frame,
    textvariable=carreta_brk_var,
    values=placa_opcoes,
    state="readonly",
    width=25
).grid(row=11, column=1)

# Ano do Cavalo

tk.Label(frame, text="Ano do Cavalo").grid(row=12, column=0, sticky="w")

ano_cavalo_entry = tk.Entry(frame, width=25)
ano_cavalo_entry.grid(row=12, column=1)

# Ano mínimo permitido

tk.Label(frame, text="Ano mínimo").grid(row=12, column=2, padx=(10, 0))

ano_minimo_var = tk.StringVar(value="2013")

ano_minimo_opcoes = [
    "2008",
    "2009",
    "2010",
    "2011",
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018"
]

ttk.Combobox(
    frame,
    textvariable=ano_minimo_var,
    values=ano_minimo_opcoes,
    state="readonly",
    width=10
).grid(row=12, column=3)

# =========================
# FROTA LEGAL
# =========================

frota_label = tk.Label(
    frame,
    text="🟢 FROTA LEGAL",
    font=("Arial", 11, "bold"),
    fg="green",
    width=20,
    anchor="w"
)

frota_label.grid(
    row=13,
    column=0,
    pady=10,
    sticky="w"
)

cadastro_opcoes = [
    "(SELECIONE)",
    "Cadastro",
    "Validar",
    "Atualizar cadastro",
    "Sem cadastro"
]

fl_checklist_var = tk.StringVar(value="(SELECIONE)")

tk.Label(frame, text="Inspeção").grid(row=14, column=0, sticky="w")

ttk.Combobox(
    frame,
    textvariable=fl_checklist_var,
    values=checklist_opcoes,
    state="readonly",
    width=25
).grid(row=14, column=1)

# =========================
# LWEB
# =========================

lweb_label = tk.Label(
    frame,
    text="🟢 LWEB",
    font=("Arial", 11, "bold"),
    fg="green",
    width=20,
    anchor="w"
)

lweb_label.grid(
    row=15,
    column=0,
    pady=10,
    sticky="w"
)

lweb_motorista_var = tk.StringVar(value="(SELECIONE)")
lweb_cavalo_var = tk.StringVar(value="(SELECIONE)")
lweb_carreta_var = tk.StringVar(value="(SELECIONE)")

tk.Label(frame, text="Motorista").grid(row=16, column=0, sticky="w")
ttk.Combobox(frame, textvariable=lweb_motorista_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=16, column=1)

tk.Label(frame, text="Cavalo").grid(row=17, column=0, sticky="w")
ttk.Combobox(frame, textvariable=lweb_cavalo_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=17, column=1)

tk.Label(frame, text="Carreta").grid(row=18, column=0, sticky="w")
ttk.Combobox(frame, textvariable=lweb_carreta_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=18, column=1)

# =========================
# BOTÕES
# =========================

frame_botoes = tk.Frame(janela)
frame_botoes.pack(pady=15)

btn_gerar = tk.Button(
    frame_botoes,
    text="GERAR VALIDAÇÃO",
    font=("Arial", 12, "bold"),
    width=20,
    command=gerar_validacao
)

btn_gerar.grid(row=0, column=0, padx=5)

btn_copiar = tk.Button(
    frame_botoes,
    text="COPIAR",
    font=("Arial", 12),
    width=15
)

btn_copiar.grid(row=0, column=1, padx=5)

btn_limpar = tk.Button(
    frame_botoes,
    text="LIMPAR",
    font=("Arial", 12),
    width=15,
    command=limpar_campos
)

btn_limpar.grid(row=0, column=2, padx=5)

# =========================
# PRÉVIA
# =========================

tk.Label(
    janela,
    text="Prévia da Validação",
    font=("Arial", 11, "bold")
).pack()

preview_text = tk.Text(
    janela,
    width=90,
    height=20
)

preview_text.pack(pady=10)

janela.bind("<F1>", preencher_status_ok)
janela.bind("<F2>", preencher_frota_ok)
janela.bind("<F3>", preencher_lweb_ok)

janela.mainloop()