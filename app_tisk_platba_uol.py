import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Pokladna",
    page_icon="🧾",
    layout="wide"
)

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


def format_kc(castka):
    try:
        return f"{float(castka):,.2f} Kč".replace(",", " ")
    except Exception:
        return str(castka)


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
            st.error(f"Nepodařilo se načíst {endpoint}: {r.status_code}")
            st.code(r.text)
            return pd.DataFrame()

        data = r.json()

        if isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, list):
            items = data
        else:
            items = []

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


def najdi_hodnotu(radek, moznosti, vychozi=""):
    for m in moznosti:
        if m in radek and pd.notna(radek[m]):
            return radek[m]
    return vychozi


if email == "SEM_DEJ_EMAIL" or token == "SEM_DEJ_NOVY_API_TOKEN":
    st.error("Doplň v kódu svůj UOL e-mail a nový API token.")
    st.stop()


# =========================
# LEVÉ MENU
# =========================
with st.sidebar:
    st.title("📋 Menu")

    st.link_button(
        "➕ Nová faktura",
        f"https://{customer_id}.ucetnictvi.uol.cz/sales/invoices/new",
        use_container_width=True
    )

    st.link_button(
        "➕ Nová účtenka",
        f"https://{customer_id}.ucetnictvi.uol.cz/sales/retails/new",
        use_container_width=True
    )

    st.divider()

    st.link_button(
        "💳 SumUp",
        "https://me.sumup.com/",
        use_container_width=True
    )

    st.divider()

    st.caption("Doklad vytvoř v UOL, potom se vrať sem a načti poslední doklad.")


# =========================
# HLAVNÍ OBRAZOVKA
# =========================
st.title("🧾 UOL – tisk dokladu a platba kartou")

st.info(
    "Vlevo klikni na **Nová faktura** nebo **Nová účtenka**. "
    "Po vytvoření dokladu v UOL se vrať sem a načti poslední doklad."
)

st.subheader("🔄 Načíst hotový doklad z UOL")

typ = st.radio(
    "Co chceš načíst?",
    ["Poslední fakturu", "Poslední účtenku"],
    horizontal=True
)

col_a, col_b = st.columns(2)

with col_a:
    nacist = st.button("🔄 Načíst poslední doklad", use_container_width=True)

with col_b:
    vymazat = st.button("🧹 Vymazat načtený doklad", use_container_width=True)

if vymazat:
    for k in ["doklad_typ", "doklad_id", "cislo", "castka", "datum"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()


if nacist:
    if typ == "Poslední fakturu":
        endpoint = "sales_invoices"
        doklad_typ = "Faktura"
    else:
        endpoint = "retails"
        doklad_typ = "Účtenka"

    df = uol_get_all(endpoint)
    radek = vyber_posledni(df)

    if radek is None:
        st.error("Žádný doklad nebyl nalezen.")
        st.stop()

    doklad_id = najdi_hodnotu(
        radek,
        [
            "invoice_id",
            "retail_id",
            "sales_retail_id",
            "gid",
            "id",
            "public_id",
            "variable_symbol",
        ]
    )

    cislo = najdi_hodnotu(
        radek,
        [
            "public_id",
            "variable_symbol",
            "invoice_id",
            "retail_id",
            "sales_retail_id",
            "gid",
            "id",
        ],
        doklad_id
    )

    castka = najdi_hodnotu(
        radek,
        [
            "total_amount",
            "amount",
            "price",
            "total_price",
            "total_price_vat_inclusive",
        ],
        ""
    )

    datum = najdi_hodnotu(
        radek,
        [
            "issue_date",
            "created_at",
            "updated_at",
        ],
        ""
    )

    st.session_state["doklad_typ"] = doklad_typ
    st.session_state["doklad_id"] = str(doklad_id)
    st.session_state["cislo"] = str(cislo)
    st.session_state["castka"] = castka
    st.session_state["datum"] = str(datum)

    st.success(f"Načteno: {doklad_typ} č. {cislo}")


# =========================
# ZOBRAZENÍ DOKLADU
# =========================
if "doklad_id" in st.session_state:
    doklad_typ = st.session_state["doklad_typ"]
    doklad_id = st.session_state["doklad_id"]
    cislo = st.session_state["cislo"]
    castka = st.session_state["castka"]
    datum = st.session_state["datum"]

    st.divider()
    st.subheader("📄 Načtený doklad")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Typ", doklad_typ)
    col2.metric("Číslo", cislo)
    col3.metric("Částka", format_kc(castka) if castka != "" else "nezjištěno")
    col4.metric("Datum", datum)

    if doklad_typ == "Faktura":
        url_pdf = f"https://{customer_id}.ucetnictvi.uol.cz/sales/invoices/{doklad_id}.pdf"
        url_uol = f"https://{customer_id}.ucetnictvi.uol.cz/sales/invoices/{doklad_id}/printing"
    else:
        url_pdf = f"https://{customer_id}.ucetnictvi.uol.cz/sales/retails/{doklad_id}.pdf"
        url_uol = f"https://{customer_id}.ucetnictvi.uol.cz/sales/retails/{doklad_id}"

    st.subheader("🖨️ Tisk / kontrola / platba")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.link_button(
            "📄 Otevřít PDF / tisk",
            url_pdf,
            use_container_width=True
        )

    with col2:
        st.link_button(
            "🔧 Otevřít doklad v UOL",
            url_uol,
            use_container_width=True
        )

    with col3:
        st.link_button(
            "💳 Otevřít SumUp",
            "https://me.sumup.com/",
            use_container_width=True
        )

    st.caption("Částku z načteného dokladu zadej do SumUp pro platbu kartou.")
else:
    st.divider()
    st.warning("Zatím není načtený žádný doklad.")
