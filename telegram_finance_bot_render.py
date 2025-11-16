
# telegram_finance_bot_render.py
#
# Bot Telegram untuk mencatat keuangan pribadi + bisnis,
# versi khusus untuk di-deploy di Render.com
#
# Cara kerja:
# - Membaca TOKEN bot & kredensial Google dari Environment Variables:
#     TELEGRAM_TOKEN      -> token dari BotFather
#     GOOGLE_CREDENTIALS  -> isi file credentials.json (service account) dalam format JSON
#     SHEET_NAME          -> (opsional) nama Google Sheet, default: Laporan_Keuangan_Full_Auto
#
# Pastikan Google Sheet punya minimal sheet:
#   - Transaksi
#   - Penjualan Bisnis
#
# Command utama:
#   /start  -> bantuan
#   /in     -> catat pemasukan
#   /out    -> catat pengeluaran
#   /sale   -> catat penjualan bisnis (sekalian ke Transaksi + Penjualan Bisnis)

import logging
import os
import json
from datetime import datetime

from telegram.ext import Updater, CommandHandler
import gspread
from google.oauth2.service_account import Credentials

# ================== KONFIGURASI GLOBAL ==================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHEET_NAME = os.getenv("SHEET_NAME", "Laporan_Keuangan_Full_Auto")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ================== GOOGLE SHEETS HELPERS ==================

def get_client():
    \"\"\"Membuat client gspread dari environment GOOGLE_CREDENTIALS.\"\"\"
    if not GOOGLE_CREDENTIALS_JSON:
        raise RuntimeError(
            "Environment variable GOOGLE_CREDENTIALS tidak ditemukan. "
            "Isi dengan JSON service account."
        )
    try:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
    except json.JSONDecodeError as e:
        raise RuntimeError("GOOGLE_CREDENTIALS bukan JSON yang valid") from e

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def get_sheets():
    \"\"\"Koneksi ke Google Sheets dan return worksheet Transaksi & Penjualan Bisnis.\"\"\"
    client = get_client()
    sh = client.open(SHEET_NAME)
    ws_transaksi = sh.worksheet("Transaksi")
    ws_bisnis = sh.worksheet("Penjualan Bisnis")
    return ws_transaksi, ws_bisnis


# ================== UTILITAS ==================

def parse_args(text, expected_parts):
    \"\"\"Helper untuk memecah argumen dengan pemisah '|'.

    Contoh pesan:
    /in 2025-11-17 | gaji | Dana | 1500000 | gaji bulan november

    expected_parts = 5 -> akan mengembalikan list 5 elemen.
    \"\"\"
    # Buang command (/in, /out, /sale)
    parts = text.split(" ", 1)
    if len(parts) < 2:
        return None
    without_command = parts[1]

    segs = [p.strip() for p in without_command.split("|")]
    if len(segs) != expected_parts:
        return None
    return segs


# ================== COMMAND HANDLERS ==================

def start(update, context):
    msg = (
        "Halo! Saya bot pencatat keuangan pribadi + bisnis.\n\n"
        "Format perintah (gunakan pemisah: | ):\n\n"
        "1) Pemasukan:\n"
        "/in TANGGAL | KATEGORI | KE_AKUN | NOMINAL | DESKRIPSI\n"
        "Contoh:\n"
        "/in 2025-11-17 | gaji | BCA | 5000000 | gaji november\n\n"
        "2) Pengeluaran:\n"
        "/out TANGGAL | KATEGORI | DARI_AKUN | NOMINAL | DESKRIPSI\n"
        "Contoh:\n"
        "/out 2025-11-18 | makan | Dana | 25000 | nasi goreng\n\n"
        "3) Penjualan bisnis:\n"
        "/sale TANGGAL | PRODUK | QTY | HARGA_JUAL_PER_UNIT | MODAL_PER_UNIT | AKUN_TERIMA | AKUN_BAYAR | CATATAN\n"
        "Contoh:\n"
        "/sale 2025-11-19 | kaos hitam | 2 | 75000 | 50000 | Dana | BCA | order ig @abc\n\n"
        "Data akan otomatis masuk ke Google Sheets dan terhubung ke ringkasan & saldo akun."
    )
    update.message.reply_text(msg)


def cmd_in(update, context):
    \"\"\"Catat pemasukan (Masuk) ke sheet Transaksi.\"\"\"
    user_text = update.message.text
    parts = parse_args(user_text, 5)
    if not parts:
        update.message.reply_text(
            "Format salah.\nContoh:\n"
            "/in 2025-11-17 | gaji | BCA | 5000000 | gaji november"
        )
        return

    tanggal_str, kategori, ke_akun, nominal_str, deskripsi = parts

    # Validasi tanggal
    try:
        tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        update.message.reply_text("Format tanggal harus YYYY-MM-DD, contoh: 2025-11-17")
        return

    # Validasi nominal
    try:
        nominal = float(nominal_str)
    except ValueError:
        update.message.reply_text("Nominal harus angka. Contoh: 150000 atau 150000.5")
        return

    try:
        ws_transaksi, _ = get_sheets()
        # Struktur: Tanggal, Jenis, Kategori, Dari Akun, Ke Akun, Nominal, Deskripsi
        ws_transaksi.append_row(
            [
                tanggal,
                "Masuk",
                kategori,
                "",  # Dari Akun (kosong, dari luar)
                ke_akun,
                nominal,
                deskripsi,
            ]
        )
    except Exception as e:
        logger.exception("Gagal menulis pemasukan ke Google Sheets")
        update.message.reply_text("Gagal menulis ke Google Sheets. Cek log & konfigurasi.")
        return

    update.message.reply_text(
        f"Pemasukan dicatat:\n"
        f"- Tanggal: {tanggal}\n"
        f"- Kategori: {kategori}\n"
        f"- Ke akun: {ke_akun}\n"
        f"- Nominal: {nominal}"
    )


def cmd_out(update, context):
    \"\"\"Catat pengeluaran (Keluar) ke sheet Transaksi.\"\"\"
    user_text = update.message.text
    parts = parse_args(user_text, 5)
    if not parts:
        update.message.reply_text(
            "Format salah.\nContoh:\n"
            "/out 2025-11-18 | makan | Dana | 25000 | nasi goreng"
        )
        return

    tanggal_str, kategori, dari_akun, nominal_str, deskripsi = parts

    # Validasi tanggal
    try:
        tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        update.message.reply_text("Format tanggal harus YYYY-MM-DD, contoh: 2025-11-18")
        return

    # Validasi nominal
    try:
        nominal = float(nominal_str)
    except ValueError:
        update.message.reply_text("Nominal harus angka. Contoh: 15000 atau 15000.5")
        return

    try:
        ws_transaksi, _ = get_sheets()
        ws_transaksi.append_row(
            [
                tanggal,
                "Keluar",
                kategori,
                dari_akun,
                "",  # Ke Akun (kosong, keluar ke luar)
                nominal,
                deskripsi,
            ]
        )
    except Exception as e:
        logger.exception("Gagal menulis pengeluaran ke Google Sheets")
        update.message.reply_text("Gagal menulis ke Google Sheets. Cek log & konfigurasi.")
        return

    update.message.reply_text(
        f"Pengeluaran dicatat:\n"
        f"- Tanggal: {tanggal}\n"
        f"- Kategori: {kategori}\n"
        f"- Dari akun: {dari_akun}\n"
        f"- Nominal: {nominal}"
    )


def cmd_sale(update, context):
    \"\"\"Catat penjualan bisnis:
    - Tambah baris ke Penjualan Bisnis (detail + profit)
    - Tambah 2 baris ke Transaksi (pemasukan & pengeluaran modal)
    \"\"\"
    user_text = update.message.text
    parts = parse_args(user_text, 8)
    if not parts:
        update.message.reply_text(
            "Format salah.\nContoh:\n"
            "/sale 2025-11-19 | kaos hitam | 2 | 75000 | 50000 | Dana | BCA | order ig @abc"
        )
        return

    (
        tanggal_str,
        produk,
        qty_str,
        harga_jual_unit_str,
        modal_unit_str,
        akun_terima,
        akun_bayar,
        catatan,
    ) = parts

    # Validasi tanggal
    try:
        tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        update.message.reply_text("Format tanggal harus YYYY-MM-DD, contoh: 2025-11-19")
        return

    # Validasi angka
    try:
        qty = float(qty_str)
        harga_jual_unit = float(harga_jual_unit_str)
        modal_unit = float(modal_unit_str)
    except ValueError:
        update.message.reply_text(
            "Qty, harga jual per unit, dan modal per unit harus berupa angka."
        )
        return

    total_jual = qty * harga_jual_unit
    total_modal = qty * modal_unit
    profit = total_jual - total_modal

    try:
        ws_transaksi, ws_bisnis = get_sheets()

        # 1) Tambah ke Penjualan Bisnis
        # Kolom: Tanggal, Produk, Qty, Harga Jual / Unit, Modal / Unit, Keuntungan, Akun Terima, Akun Bayar, Catatan
        ws_bisnis.append_row(
            [
                tanggal,
                produk,
                qty,
                harga_jual_unit,
                modal_unit,
                profit,
                akun_terima,
                akun_bayar,
                catatan,
            ]
        )

        # 2) Tambah ke Transaksi: pemasukan dari customer
        ws_transaksi.append_row(
            [
                tanggal,
                "Masuk",
                f"Penjualan {produk}",
                "Customer",
                akun_terima,
                total_jual,
                catatan,
            ]
        )

        # 3) Tambah ke Transaksi: pengeluaran modal ke supplier
        ws_transaksi.append_row(
            [
                tanggal,
                "Keluar",
                f"Modal {produk}",
                akun_bayar,
                "Supplier",
                total_modal,
                catatan,
            ]
        )

    except Exception as e:
        logger.exception("Gagal menulis penjualan bisnis ke Google Sheets")
        update.message.reply_text("Gagal menulis ke Google Sheets. Cek log & konfigurasi.")
        return

    update.message.reply_text(
        "Penjualan bisnis dicatat:\n"
        f"- Produk : {produk}\n"
        f"- Qty    : {qty}\n"
        f"- Total jual : {total_jual}\n"
        f"- Total modal: {total_modal}\n"
        f"- Profit     : {profit}\n"
        f"- Terima di  : {akun_terima}\n"
        f"- Bayar dari : {akun_bayar}"
    )


# ================== MAIN ==================

def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "Environment variable TELEGRAM_TOKEN tidak di-set. "
            "Isi dengan token dari BotFather di Render."
        )

    logger.info("Start bot dengan SHEET_NAME=%s", SHEET_NAME)

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("in", cmd_in))
    dp.add_handler(CommandHandler("out", cmd_out))
    dp.add_handler(CommandHandler("sale", cmd_sale))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
