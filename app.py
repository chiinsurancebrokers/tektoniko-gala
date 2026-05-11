import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io, json
from datetime import datetime

st.set_page_config(page_title="Εκδήλωση · ΑΚΡΟΠΟΛΙΣ 84", page_icon="🎭", layout="centered")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.poster-box{background:linear-gradient(135deg,#0d1b2a,#1a3a5c);border-radius:14px;
  padding:20px 24px;color:#fff;margin-bottom:24px}
.poster-title{font-size:10px;letter-spacing:3px;color:#90b8d4;text-transform:uppercase;margin-bottom:6px}
.poster-main{font-size:22px;font-weight:700;margin-bottom:4px}
.poster-sub{font-size:13px;color:#90b8d4;margin-bottom:12px}
.poster-detail{font-size:13px;color:#cde;margin-bottom:2px}
.badge-paid{background:#EAF3DE;color:#3B6D11;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}
.badge-pending{background:#FAEEDA;color:#854F0B;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}
.metric-row{display:flex;gap:12px;margin-bottom:24px}
</style>
""", unsafe_allow_html=True)

# ── Password ─────────────────────────────────────────────────────────────────
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("### 🔒 Στ∴ ΑΚΡΟΠΟΛΙΣ 84")
    pin = st.text_input("Κωδικός πρόσβασης", type="password")
    if st.button("Είσοδος", type="primary"):
        if pin == "8426":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Λάθος κωδικός")
    st.stop()

# ── Google Services ───────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

@st.cache_resource
def get_services():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES)
    gc = gspread.authorize(creds)
    drive = build("drive", "v3", credentials=creds)
    return gc, drive

@st.cache_data(ttl=10)
def load_sheet(sheet_name):
    gc, _ = get_services()
    sh = gc.open_by_key(st.secrets["sheet_id"])
    ws = sh.worksheet(sheet_name)
    return ws.get_all_records()

def get_worksheet(sheet_name):
    gc, _ = get_services()
    sh = gc.open_by_key(st.secrets["sheet_id"])
    return sh.worksheet(sheet_name)

def upload_to_drive(file_bytes, filename, person_name):
    _, drive = get_services()
    folder_id = st.secrets.get("drive_folder_id", None)
    meta = {"name": f"{person_name} - {filename}"}
    if folder_id:
        meta["parents"] = [folder_id]
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype="application/octet-stream")
    f = drive.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()
    drive.permissions().create(fileId=f["id"], body={"role":"reader","type":"anyone"}).execute()
    return f["webViewLink"]

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 2.5])
with col1:
    try:
        st.image("/mnt/user-data/uploads/Screenshot_2026-05-10_at_10_11_15_PM.png", use_container_width=True)
    except:
        pass
with col2:
    st.markdown("""
    <div class="poster-box">
      <div class="poster-title">Φιλανθρωπική Εκδήλωση Τεκτονικού Ιδρύματος</div>
      <div class="poster-main">Από τον Πλέσσα στον Αλμοδόβαρ</div>
      <div class="poster-sub">τα θρυλικά τραγούδια της μεγάλης οθόνης</div>
      <div class="poster-detail">🎤 Ιωάννα Σεβοπούλου</div>
      <div class="poster-detail">📅 Δευτέρα 8 Ιουνίου 2026 · 19:30</div>
      <div class="poster-detail">📍 ΦΑΡΟΣ, ΚΠΙΣΝ</div>
      <br><span style="background:#185FA5;color:#fff;padding:5px 14px;border-radius:20px;font-size:13px;font-weight:600">Πρόσκληση €60</span>
    </div>
    """, unsafe_allow_html=True)

# ── Load data ──────────────────────────────────────────────────────────────────
try:
    attending = load_sheet("Συμμετέχοντες")
    declined  = load_sheet("Δεν_Έρχονται")
except Exception as e:
    import traceback
    st.error(f"Σφάλμα σύνδεσης με Google Sheets: {type(e).__name__}: {e}")
    st.code(traceback.format_exc())
    st.write("Secrets keys:", list(st.secrets.keys()))
    st.stop()

total_tickets = sum(r.get("Προσκλήσεις", 0) for r in attending)
paid_count    = sum(1 for r in attending if r.get("Πληρωμένο") == "ΝΑΙ")
pending_count = len(attending) - paid_count

# ── Metrics ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Σύνολο προσκλήσεων", total_tickets)
c2.metric("Έχουν πληρώσει", paid_count)
c3.metric("Εκκρεμεί κατάθεση", pending_count)
c4.metric("Δεν έρχονται", len(declined))

st.divider()

# ── Συμμετέχοντες ─────────────────────────────────────────────────────────────
st.subheader(f"Συμμετέχοντες ({len(attending)} άτομα · {total_tickets} προσκλήσεις)")

for i, row in enumerate(attending):
    with st.container(border=True):
        cols = st.columns([3, 1.5, 1.5, 2])
        cols[0].markdown(f"**{row['Ονοματεπώνυμο']}**  \n_{row['Προσκλήσεις']} προσκλήσεις_")
        
        paid = row.get("Πληρωμένο") == "ΝΑΙ"
        if cols[1].button("✓ Πληρωμένο" if paid else "⏳ Εκκρεμεί", key=f"pay_{i}",
                          type="primary" if paid else "secondary"):
            ws = get_worksheet("Συμμετέχοντες")
            new_val = "ΟΧΙ" if paid else "ΝΑΙ"
            cell = ws.find(row["Ονοματεπώνυμο"])
            ws.update_cell(cell.row, 5, new_val)
            load_sheet.clear()
            st.rerun()
        
        receipt_url = row.get("Απόδειξη_URL", "")
        if receipt_url:
            cols[2].link_button("📎 Drive", receipt_url)
        else:
            uploaded = cols[2].file_uploader("Απόδειξη", key=f"rec_{i}",
                                              label_visibility="collapsed",
                                              type=["jpg","jpeg","png","pdf"])
            if uploaded:
                with st.spinner("Ανέβασμα στο Drive..."):
                    url = upload_receipt(uploaded.read(), uploaded.name)
                    ws = get_worksheet("Συμμετέχοντες")
                    cell = ws.find(row["Ονοματεπώνυμο"])
                    ws.update_cell(cell.row, 6, url)
                    ws.update_cell(cell.row, 5, "ΝΑΙ")
                    load_sheet.clear()
                    st.success("✓ Ανέβηκε!")
                    st.rerun()

# ── Προσθήκη συμμετέχοντα ────────────────────────────────────────────────────
with st.expander("+ Προσθήκη συμμετέχοντα"):
    n1, n2 = st.columns([3,1])
    new_name    = n1.text_input("Ονοματεπώνυμο", key="new_name")
    new_tickets = n2.number_input("Προσκλήσεις", 1, 4, 2, key="new_tickets")
    if st.button("Αποθήκευση", type="primary", key="save_attend"):
        if new_name.strip():
            ws = get_worksheet("Συμμετέχοντες")
            ws.append_row([new_name.strip(), new_tickets, datetime.now().strftime("%d/%m/%Y"), "", "ΟΧΙ", ""])
            load_sheet.clear()
            st.rerun()

st.divider()

# ── Δεν θα παραστούν ──────────────────────────────────────────────────────────
st.subheader(f"Δεν θα παραστούν ({len(declined)})")

for row in declined:
    with st.container(border=True):
        st.markdown(f"<span style='color:#888'>{row['Ονοματεπώνυμο']}</span>", unsafe_allow_html=True)

with st.expander("+ Προσθήκη"):
    dec_name = st.text_input("Ονοματεπώνυμο", key="dec_name")
    if st.button("Αποθήκευση", type="primary", key="save_dec"):
        if dec_name.strip():
            ws = get_worksheet("Δεν_Έρχονται")
            ws.append_row([dec_name.strip(), datetime.now().strftime("%d/%m/%Y")])
            load_sheet.clear()
            st.rerun()
