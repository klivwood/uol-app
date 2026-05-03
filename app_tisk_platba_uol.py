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
.block-container {
    padding-top: 1rem;
    max-width: 1100px;
}

h1 {
    text-align: center;
    font-size: 46px !important;
}

h2, h3 {
    text-align: center;
    font-size: 30px !important;
}

.stButton > button,
.stLinkButton > a {
    width: 100%;
    height: 85px;
    font-size: 28px;
    font-weight: 800;
    border-radius: 18px;
}

[data-testid="stMetricValue"] {
    font-size: 36px !important;
    font-weight: 800;
}

[data-testid="stMetricLabel"] {
    font-size: 20px !important;
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


def nacti_doklad(typ):
    if typ == "Faktura":
        endpoint = "sales_invoices"
        doklad_typ = "Faktura"
    else:
        endpoint = "retails"
        doklad_typ = "Účtenka"

    df = uol_get_all(endpoint)
    radek = vyber_posledni(df)

    if radek is None:
        st.error("Žádný doklad nebyl nalezen.")
        return

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
# MENU
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


# =========================
# HLAVNÍ OBRAZOVKA
# =========================
st.title("🧾 POKLADNA")

st.markdown('<div class="big-card">', unsafe_allow_html=True)

typ_nacteni = st.radio(
    "Co načíst?",
    ["Faktura", "Účtenka"],
    horizontal=True
)

col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 NAČÍST POSLEDNÍ", use_container_width=True):
        nacti_doklad(typ_nacteni)

with col2:
    if st.button("🧹 VYMAZAT", use_container_width=True):
        for k in ["doklad_typ", "doklad_id", "cislo", "castka", "datum"]:
            st.session_state.pop(k, None)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# =========================
# NAČTENÝ DOKLAD
# =========================
if "doklad_id" in st.session_state:
    doklad_typ = st.session_state["doklad_typ"]
    doklad_id = st.session_state["doklad_id"]
    cislo = st.session_state["cislo"]
    castka = st.session_state["castka"]
    datum = st.session_state["datum"]

    st.markdown('<div class="big-card">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    c1.metric("Typ", doklad_typ)
    c2.metric("Číslo", cislo)
    c3.metric("Částka", format_kc(castka) if castka != "" else "nezjištěno")

    st.markdown(f"### Datum: {datum}")

    st.markdown('</div>', unsafe_allow_html=True)

    if doklad_typ == "Faktura":
        url_pdf = f"https://{customer_id}.ucetnictvi.uol.cz/sales/invoices/{doklad_id}.pdf"
        url_uol = f"https://{customer_id}.ucetnictvi.uol.cz/sales/invoices/{doklad_id}/printing"
    else:
        url_pdf = f"https://{customer_id}.ucetnictvi.uol.cz/sales/retails/{doklad_id}.pdf"
        url_uol = f"https://{customer_id}.ucetnictvi.uol.cz/sales/retails/{doklad_id}"

    st.subheader("Akce")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.link_button(
            "📄 TISK",
            url_pdf,
            use_container_width=True
        )

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
    st.link_button(
        "🔄 Otevřít SumUp",
        "https://me.sumup.com/",
        use_container_width=True
    )

else:
    st.warning("Zatím není načtený žádný doklad.")
