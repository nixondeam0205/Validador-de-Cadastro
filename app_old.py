import tkinter as tk
from tkinter import ttk

def converter_status(valor):

    mapa = {
    "OK": "✅ OK",
    "Renovar": "⚠️ Renovar",
    "Em análise": "⚠️ Em análise",
    "Inapto": "❌ Inapto",
    "Vencido": "⚠️ Vencido",
    "Sem checklist": "❌ Sem checklist",
    "Cadastro": "✅ Cadastro",
    "Atualizar cadastro": "⚠️ Atualizar cadastro",
    "Sem cadastro": "❌ Sem cadastro"
}

    return mapa.get(valor, valor)

def gerar_validacao():

    motorista1 = motorista1_entry.get().strip()
    motorista2 = motorista2_entry.get().strip()
    cpf1 = cpf1_entry.get().strip()
    cpf2 = cpf2_entry.get().strip()

    cavalo = cavalo_entry.get().strip().upper()
    carreta = carreta_entry.get().strip().upper()
    ano_cavalo = ano_cavalo_entry.get().strip()

    tem_carreta = possui_carreta_var.get()

    status_carreta = ""
    frota_carreta = ""
    lweb_carreta = ""

    if tem_carreta:

        status_carreta = (
            f"\nPlaca Carreta BRK: "
            f"{converter_status(carreta_brk_var.get())}"
        )

        frota_carreta = (
            f"\nCarreta: "
            f"{converter_status(fl_carreta_var.get())}"
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

    texto = f"""🚛 VALIDAÇÃO DE CADASTRO

{motorista_texto}

🚛 Placas:
{placas}

━━━━━━━━━━━━━━━
📋 STATUS

BRK: {converter_status(brk_var.get())}
Onboarding: {converter_status(onboarding_var.get())}
ET: {converter_status(et_var.get())}
TDD: {converter_status(tdd_var.get())}
Checklist: {converter_status(checklist_var.get())}
Placa Cavalo BRK: {converter_status(cavalo_brk_var.get())}{status_carreta}
Ano do Cavalo: {ano_cavalo}

━━━━━━━━━━━━━━━
🚛 FROTA LEGAL

Motorista: {converter_status(fl_motorista_var.get())}
Cavalo: {converter_status(fl_cavalo_var.get())}{frota_carreta}

━━━━━━━━━━━━━━━
⚠️ LWEB

Motorista: {converter_status(lweb_motorista_var.get())}
Cavalo: {converter_status(lweb_cavalo_var.get())}{lweb_carreta}
"""

    if (
        lweb_motorista_var.get() == "Sem cadastro"
        or lweb_cavalo_var.get() == "Sem cadastro"
        or (
            tem_carreta
            and lweb_carreta_var.get() == "Sem cadastro"
        )
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

Nosso processo de cadastro é realizado 100% pelo próprio motorista, diretamente pelo aplicativo ou via navegador.

1) Passo:

📲 Baixe o aplicativo:
https://play.google.com/store/apps/details?id=br.com.linehaul_driver&pcampaignid=web_share

2) Passo:

🟠 Acesse o cadastro:
https://losunglm.com.br/cad_v2/

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

def limpar_campos():

    motorista1_entry.delete(0, tk.END)
    motorista2_entry.delete(0, tk.END)
    cpf1_entry.delete(0, tk.END)
    cpf2_entry.delete(0, tk.END)

    cavalo_entry.delete(0, tk.END)
    carreta_entry.delete(0, tk.END)
    ano_cavalo_entry.delete(0, tk.END)
    possui_carreta_var.set(True)

    brk_var.set("OK")
    onboarding_var.set("OK")
    et_var.set("OK")
    tdd_var.set("OK")
    checklist_var.set("OK")

    cavalo_brk_var.set("OK")
    carreta_brk_var.set("OK")

    fl_motorista_var.set("Cadastro")
    fl_cavalo_var.set("Cadastro")
    fl_carreta_var.set("Cadastro")

    lweb_motorista_var.set("Cadastro")
    lweb_cavalo_var.set("Cadastro")
    lweb_carreta_var.set("Cadastro")

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


janela = tk.Tk()

janela.title("Validador de Cadastro")
janela.geometry("850x900")

titulo = tk.Label(
    janela,
    text="🚛 VALIDADOR DE CADASTRO",
    font=("Arial", 16, "bold")
)

titulo.pack(pady=10)

frame = tk.Frame(janela)
frame.pack(pady=5)

# =========================
# DADOS
# =========================

tk.Label(frame, text="Motorista 1").grid(row=0, column=0, sticky="w")

motorista1_entry = tk.Entry(frame, width=30)
motorista1_entry.grid(row=0, column=1)

tk.Label(frame, text="CPF").grid(row=0, column=2, padx=(10,0))

cpf1_entry = tk.Entry(frame, width=18)
cpf1_entry.grid(row=0, column=3)
cpf1_entry.bind("<KeyRelease>", formatar_cpf)

tk.Label(frame, text="Motorista 2").grid(row=1, column=0, sticky="w")

motorista2_entry = tk.Entry(frame, width=30)
motorista2_entry.grid(row=1, column=1)

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

tk.Label(
    frame,
    text="📋 STATUS",
    font=("Arial", 11, "bold")
).grid(row=4, column=0, pady=10)

status_padrao = [
    "OK",
    "Renovar",
    "Inapto"
]

checklist_opcoes = [
    "OK",
    "Vencido",
    "Sem checklist"
]

placa_opcoes = [
    "OK",
    "Renovar",
    "Em análise",
    "Inapto",
    "Sem cadastro"
]

# BRK

tk.Label(frame, text="BRK").grid(row=5, column=0, sticky="w")

brk_var = tk.StringVar(value="OK")

brk_opcoes = [
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

onboarding_var = tk.StringVar(value="OK")

ttk.Combobox(
    frame,
    textvariable=onboarding_var,
    values=status_padrao,
    state="readonly",
    width=25
).grid(row=6, column=1)

# ET

tk.Label(frame, text="ET").grid(row=7, column=0, sticky="w")

et_var = tk.StringVar(value="OK")

ttk.Combobox(
    frame,
    textvariable=et_var,
    values=status_padrao,
    state="readonly",
    width=25
).grid(row=7, column=1)

# TDD

tk.Label(frame, text="TDD").grid(row=8, column=0, sticky="w")

tdd_var = tk.StringVar(value="OK")

ttk.Combobox(
    frame,
    textvariable=tdd_var,
    values=status_padrao,
    state="readonly",
    width=25
).grid(row=8, column=1)

# Checklist

tk.Label(frame, text="Checklist").grid(row=9, column=0, sticky="w")

checklist_var = tk.StringVar(value="OK")

ttk.Combobox(
    frame,
    textvariable=checklist_var,
    values=checklist_opcoes,
    state="readonly",
    width=25
).grid(row=9, column=1)

# Cavalo BRK

tk.Label(frame, text="Placa Cavalo BRK").grid(row=10, column=0, sticky="w")

cavalo_brk_var = tk.StringVar(value="OK")

ttk.Combobox(
    frame,
    textvariable=cavalo_brk_var,
    values=placa_opcoes,
    state="readonly",
    width=25
).grid(row=10, column=1)

# Carreta BRK

tk.Label(frame, text="Placa Carreta BRK").grid(row=11, column=0, sticky="w")

carreta_brk_var = tk.StringVar(value="OK")

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

# =========================
# FROTA LEGAL
# =========================

tk.Label(
    frame,
    text="🚛 FROTA LEGAL",
    font=("Arial", 11, "bold")
).grid(row=13, column=0, pady=10)

cadastro_opcoes = [
    "Cadastro",
    "Atualizar cadastro",
    "Sem cadastro"
]

fl_motorista_var = tk.StringVar(value="Cadastro")
fl_cavalo_var = tk.StringVar(value="Cadastro")
fl_carreta_var = tk.StringVar(value="Cadastro")

tk.Label(frame, text="Motorista").grid(row=14, column=0, sticky="w")
ttk.Combobox(frame, textvariable=fl_motorista_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=14, column=1)

tk.Label(frame, text="Cavalo").grid(row=15, column=0, sticky="w")
ttk.Combobox(frame, textvariable=fl_cavalo_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=15, column=1)

tk.Label(frame, text="Carreta").grid(row=16, column=0, sticky="w")
ttk.Combobox(frame, textvariable=fl_carreta_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=16, column=1)

# =========================
# LWEB
# =========================

tk.Label(
    frame,
    text="⚠️ LWEB",
    font=("Arial", 11, "bold")
).grid(row=17, column=0, pady=10)

lweb_motorista_var = tk.StringVar(value="Cadastro")
lweb_cavalo_var = tk.StringVar(value="Cadastro")
lweb_carreta_var = tk.StringVar(value="Cadastro")

tk.Label(frame, text="Motorista").grid(row=18, column=0, sticky="w")
ttk.Combobox(frame, textvariable=lweb_motorista_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=18, column=1)

tk.Label(frame, text="Cavalo").grid(row=19, column=0, sticky="w")
ttk.Combobox(frame, textvariable=lweb_cavalo_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=19, column=1)

tk.Label(frame, text="Carreta").grid(row=20, column=0, sticky="w")
ttk.Combobox(frame, textvariable=lweb_carreta_var,
             values=cadastro_opcoes,
             state="readonly",
             width=25).grid(row=20, column=1)

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

janela.mainloop()