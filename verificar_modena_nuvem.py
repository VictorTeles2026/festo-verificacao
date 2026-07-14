"""
Verifica se a Modena21 Automação e Controle aparece como distribuidora Festo
em São Paulo e Rio de Janeiro. Envia email com o resultado.
Usado pelo GitHub Actions — credenciais vêm de variáveis de ambiente.
"""

import asyncio
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.async_api import async_playwright

EMPRESA_BUSCADA = "Modena21 Automação e Controle"
CIDADES = ["São Paulo", "Rio de Janeiro"]

EMAIL_REMETENTE   = os.environ["GMAIL_USER"]
EMAIL_SENHA_APP   = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_DESTINATARIO = os.environ["GMAIL_USER"]


async def verificar_cidade(browser, cidade: str) -> dict:
    print(f"  Buscando em {cidade}...")
    page = await browser.new_page()
    try:
        await page.goto("https://distributorlocator.festo.com/?locale=br-pt", timeout=30000)
        await page.wait_for_timeout(5000)

        campo = page.locator("input").first
        await campo.click()
        await campo.fill(cidade)
        await page.wait_for_timeout(2000)

        sugestao = page.locator("li, [role='option'], [class*='suggestion'], [class*='autocomplete']").first
        try:
            await sugestao.click(timeout=3000)
        except Exception:
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(2000)

        try:
            botao = page.locator("button, input[type='submit']").filter(has_text="Exibir")
            await botao.click(timeout=5000)
        except Exception:
            pass

        await page.wait_for_timeout(6000)

        texto = await page.evaluate("document.body.innerText")
        encontrada = EMPRESA_BUSCADA.lower() in texto.lower()
        return {"cidade": cidade, "encontrada": encontrada}

    except Exception as e:
        return {"cidade": cidade, "encontrada": False, "erro": str(e)}
    finally:
        await page.close()


def enviar_email(resultados: list):
    hoje = datetime.now().strftime("%d/%m/%Y")

    linhas_html = []
    linhas_texto = []
    for r in resultados:
        if r.get("encontrada"):
            emoji, status, cor = "✅", "ENCONTRADA", "#2d7a2d"
        else:
            emoji, status, cor = "❌", "NÃO encontrada", "#b33000"
        linhas_html.append(
            f'<tr><td style="padding:8px 16px">{r["cidade"]}</td>'
            f'<td style="padding:8px 16px;color:{cor};font-weight:bold">{emoji} {status}</td></tr>'
        )
        linhas_texto.append(f"{r['cidade']}: {emoji} {status}")

    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222">
      <h2 style="color:#003366">📋 Verificação Festo – Modena21</h2>
      <p>{hoje}</p>
      <table border="1" cellspacing="0" cellpadding="0"
             style="border-collapse:collapse;border-color:#ccc">
        <thead>
          <tr style="background:#003366;color:white">
            <th style="padding:8px 16px">Cidade</th>
            <th style="padding:8px 16px">Status</th>
          </tr>
        </thead>
        <tbody>{"".join(linhas_html)}</tbody>
      </table>
      <p style="margin-top:20px;font-size:12px;color:#888">
        Verificado automaticamente em distributorlocator.festo.com
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Festo] Modena21 – {hoje}"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINATARIO
    msg.attach(MIMEText("\n".join(linhas_texto), "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        s.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIO, msg.as_string())
    print("Email enviado.")


async def main():
    print(f"Verificacao Festo – {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    resultados = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for cidade in CIDADES:
            r = await verificar_cidade(browser, cidade)
            resultados.append(r)
        await browser.close()

    for r in resultados:
        status = "ENCONTRADA" if r.get("encontrada") else "nao encontrada"
        print(f"  {r['cidade']}: {status}")

    enviar_email(resultados)


if __name__ == "__main__":
    asyncio.run(main())
