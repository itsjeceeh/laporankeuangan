# ===============================================================
#  telegram_finance_bot_render.py
#  CLEAN VERSION – Untuk Hosting di Render (100% bebas error)
# ===============================================================

import logging
import os
import json
from datetime import datetime

from telegram.ext import Updater, CommandHandler
import gspread
from google.oauth2.service_account import Credentials

# ================== KONFIG ==================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHEET_NAME = os.getenv("SHEET_NAME", "Laporan_Keuangan_Full_Auto")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ================== GOOGLE SHEETS ==================

def get_client():
    """Buat koneksi ke Google Sheets dari ENV GOOGLE_CREDENTIALS."""
    if not GOOGLE_CREDENTIALS_JSON:
        raise RuntimeError("Environment GOOGLE_CREDENTIALS tidak ditemukan di Render.")

    info = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)

    return gspread.authorize(creds)


def get_sheets():
    client = get_client()
    sh = client.open(SHEET_NAME)
    ws_transaksi = sh.worksheet("Transaksi")
    ws_bisnis = sh.worksheet("Penjualan Bisnis")
    return ws_transaksi, ws_bisnis


# ================== UTILITAS ==================

def parse_args(text, expected_parts):
    """Parsing command: /cmd arg1 | arg2 | arg3"""
    parts = text.split(" ", 1)
    if len(parts) < 2:
        return None
    raw = parts[1]
    segs = [p.strip() for p in raw.split("|")]
    return segs if len(segs) == expected_parts else None


# ================== COMMAND HANDLERS ==================

def start(update, context):
    msg = (
        "Bot Keuangan Aktif.\n\n"
        "Format:\n\n"
        "/in TGL | KATEGORI | KE AKUN | NOMINAL | CATATAN\n"
        "/out TGL | KATEGORI | DARI AKUN | NOMINAL | CATATAN\n"
        "/sale TGL | PRODUK | QTY | HARGA_JUAL | MODAL | AKUN_TERIMA | AKUN_BAYAR | CATATAN\n"
    )
    update.message.reply_text(msg)


# ---------- Pemasukan ----------
def cmd_in(update, context):
    parts = parse_args(update.message.text, 5)
    if not parts:
        update.message.reply_text("Format salah.")
        return

    tgl, kategori, akun, nominal_str, desc = parts

    try:
        tgl = datetime.strptime(tgl, "%Y-%m-%d").strftime("%Y-%m-%d")
        nominal = float(nominal_str)
    except:
        update.message.reply_text("Tanggal/nominal tidak valid.")
        return

    ws_transaksi, _ = get_sheets()

    ws_transaksi.append_row([
        tgl, "Masuk", kategori, "", akun, nominal, desc
    ])

    update.message.reply_text(f"Pemasukan dicatat ke {akun}: {nominal}")


# ---------- Pengeluaran ----------
def cmd_out(update, context):
    parts = parse_args(update.message.text, 5)
    if not parts:
        update.message.reply_text("Format salah.")
        return

    tgl, kategori, akun, nominal_str, desc = parts

    try:
        tgl = datetime.strptime(tgl, "%Y-%m-%d").strftime("%Y-%m-%d")
        nominal = float(nominal_str)
    except:
        update.message.reply_text("Tanggal/nominal tidak valid.")
        return

    ws_transaksi, _ = get_sheets()

    ws_transaksi.append_row([
        tgl, "Keluar", kategori, akun, "", nominal, desc
    ])

    update.message.reply_text(f"Pengeluaran dicatat dari {akun}: {nominal}")


# ---------- Penjualan Bisnis ----------
def cmd_sale(update, context):
    parts = parse_args(update.message.text, 8)
    if not parts:
        update.message.reply_text("Format salah.")
        return

    (
        tgl, produk, qty_str, harga_str,
        modal_str, akun_in, akun_out, catatan
    ) = parts

    try:
        tgl = datetime.strptime(tgl, "%Y-%m-%d").strftime("%Y-%m-%d")
        qty = float(qty_str)
        harga = float(harga_str)
        modal = float(modal_str)
    except:
        update.message.reply_text("Data tidak valid.")
        return

    total_jual = qty * harga
    total_modal = qty * modal
    profit = total_jual - total_modal

    ws_transaksi, ws_bisnis = get_sheets()

    # Sheet Penjualan Bisnis
    ws_bisnis.append_row([
        tgl, produk, qty, harga, modal, profit, akun_in, akun_out, catatan
    ])

    # Sheet Transaksi - pemasukan
    ws_transaksi.append_row([
        tgl, "Masuk", f"Penjualan {produk}", "Customer",
        akun_in, total_jual, catatan
    ])

    # Sheet Transaksi - modal keluar
    ws_transaksi.append_row([
        tgl, "Keluar", f"Modal {produk}", akun_out,
        "Supplier", total_modal, catatan
    ])

    update.message.reply_text(f"Penjualan dicatat. Profit: {profit}")


# ================== MAIN ==================

def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN tidak ditemukan di Render.")

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("in", cmd_in))
    dp.add_handler(CommandHandler("out", cmd_out))
    dp.add_handler(CommandHandler("sale", cmd_sale))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()


