import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Pokladna",
    page_icon="🧾",
    layout="wide"
)

st.markdown("""
<style>
.block-container { padding-top: 1rem; max-width: 1100px; }
h1 { text-align: center; font-size: 46px !important; }
h2, h3 { text-align: center; font-size: 30px !important; }

.stButton > button,
.stLinkButton > a {
    width: 100%;
    height: 85px;
    font-size: 28px;
    font-weight: 800;
    border-radius: 18px;
}

.big-card {
    background: #f6f8fb;
    border-radius: 22px;
    padding: 25px;
    margin: 15px 0;
    border: 1px solid #e1e5ea;
}
</style>
""", unsafe_allow_html=True)

# =========================
# NASTAVENÍ
# =========================
customer_id = "klivwood"
email = st.secrets["uol_email"]
token = st.secrets["uol_token"]

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# =========================
# FUNKCE
# =========================
def format_kc(c):
    try:
        return f"{float(c):,.2f} Kč".replace(",", " ")
    except:
        return str(c)

def endpoint_podle_typu(typ):
    return ("sales_invoices", "Faktura") if typ == "Faktura" else ("retails", "Účtenka")

def uol_get_all(endpoint):
    vse = []
    page = 1

    while True:
        url = f"https://{customer_id}.ucetnictvi.uol.cz/api/v1/{endpoint}"

        r = requests.get(
            url,
            auth=(email, token),
            headers=headers,
            params={"page": page, "per_page": 250},
            timeout=30
        )

        if r.status_code != 200:
            st.error(f"Chyba: {r.status_code}")
            return pd.DataFrame()

        data = r.json()
        items = data["items"] if isinstance(data, dict) and "items" in data else data

        if not items:
            break

        vse.extend(items)

        if len(items) < 250:
            break

        page += 1

    return pd.json_normalize(vse)

def vyber_posledni(df):
    if df.empty:
        return None
    for col in ["created_at", "updated_at", "issue_date"]:
        if col in df.columns:
            return df.sort_values(col, ascending=False).iloc[0]
    return df.iloc[0]

def najdi(radek, moznosti, vychozi=""):
    for m in moznosti:
        if m in radek and pd.notna(radek[m]):
            return radek[m]
    return vychozi

def uloz(radek, typ):
    doklad_id = najdi(radek, ["id","public_id","invoice_id","retail_id"])
    cislo = najdi(radek, ["public_id","variable_symbol"], doklad_id)
    castka = najdi(radek, ["total_amount","amount","price"], "")
    datum = najdi(radek, ["issue_date","created_at"], "")

    st.session_state.update({
        "doklad_typ": typ,
        "doklad_id": str(doklad_id),
        "cislo": str(cislo),
        "castka": castka,
        "datum": str(datum)
    })

def nacti_posledni(typ):
    endpoint, t = endpoint_podle_typu(typ)
    df = uol_get_all(endpoint)
    radek = vyber_posledni(df)
    if radek is not None:
        uloz(radek, t)

def nacti_seznam(typ):
    endpoint, _ = endpoint_podle_typu(typ)
    df = uol_get_all(endpoint)
    st.session_state["seznam"] = df.to_dict("records")

# =========================
# UI
# =========================
st.title("🧾 POKLADNA")

typ = st.radio("Typ", ["Faktura","Účtenka"], horizontal=True)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Poslední"):
        nacti_posledni(typ)

with col2:
    if st.button("📋 Seznam"):
        nacti_seznam(typ)

with col3:
    if st.button("🧹 Reset"):
        st.session_state.clear()

# =========================
# VÝBĚR ZE SEZNAMU
# =========================
if "seznam" in st.session_state:
    seznam = st.session_state["seznam"]

    vyber = st.selectbox(
        "Vyber doklad",
        range(len(seznam)),
        format_func=lambda i: str(seznam[i].get("public_id","doklad"))
    )

    if st.button("Načíst vybraný"):
        _, t = endpoint_podle_typu(typ)
        uloz(seznam[vyber], t)

# =========================
# DETAIL
# =========================
if "doklad_id" in st.session_state:
    st.subheader("Doklad")

    st.metric("Typ", st.session_state["doklad_typ"])
    st.metric("Číslo", st.session_state["cislo"])
    st.metric("Částka", format_kc(st.session_state["castka"]))

    castka = st.session_state["castka"]
    doklad_id = st.session_state["doklad_id"]

    if st.session_state["doklad_typ"] == "Faktura":
        url_pdf = f"https://{customer_id}.ucetnictvi.uol.cz/sales/invoices/{doklad_id}.pdf"
    else:
        url_pdf = f"https://{customer_id}.ucetnictvi.uol.cz/sales/retails/{doklad_id}.pdf"

    st.subheader("Akce")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.link_button("📄 TISK", url_pdf)

    with col2:
        castka_float = float(castka) if castka != "" else 0

        st.markdown(f"""
        <a href="sumupmerchant://pay/{castka_float}">
            <button style="
                width:100%;
                height:85px;
                font-size:28px;
                font-weight:800;
                border-radius:18px;
                background:#28a745;
                color:white;
            ">
                💳 ZAPLATIT {format_kc(castka)}
            </button>
        </a>
        """, unsafe_allow_html=True)

    with col3:
        st.link_button("🔄 Otevřít SumUp", "https://me.sumup.com/")

else:
    st.warning("Žádný doklad")
