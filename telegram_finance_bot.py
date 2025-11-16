
    # telegram_finance_bot.py
    #
    # Bot Telegram untuk mencatat:
    # - Pemasukan
    # - Pengeluaran
    # - Penjualan bisnis (otomatis ke 2 sheet: Transaksi & Penjualan Bisnis)
    #
    # Dibuat agar formatnya cocok dengan file: Laporan_Keuangan_Full_Auto
    #
    # REQUIREMENTS (install dulu):
    #   pip install python-telegram-bot==13.15 gspread google-auth
    #
    # SEBELUM JALAN:
    # 1. Buat bot di BotFather, ambil TOKEN -> isi di TELEGRAM_TOKEN di bawah.
    # 2. Upload template ke Google Sheets, beri nama sesuai SHEET_NAME.
    # 3. Buat Service Account (Google Cloud), download file JSON -> simpan sebagai credentials.json
    # 4. Share Google Sheet ke email service account dengan akses Editor.

    import logging
    from datetime import datetime

    from telegram.ext import Updater, CommandHandler
    import gspread
    from google.oauth2.service_account import Credentials

    # ================== KONFIGURASI ==================

    TELEGRAM_TOKEN = "8246749244:AAHOQmiwDiP5O08FTIxZ-JOAOR9oOaCbqj4"
    SHEET_NAME = "LaporanKeuangan"  # ganti sesuai nama di Google Sheets Anda

    # Scope untuk Google Sheets API
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    # File credentials service account
    SERVICE_ACCOUNT_FILE = "credentials.json"

    # =================================================

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logger = logging.getLogger(__name__)


    def get_sheets():
        """Koneksi ke Google Sheets dan return worksheet yang dibutuhkan."""
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sh = client.open(SHEET_NAME)
        ws_transaksi = sh.worksheet("Transaksi")
        ws_bisnis = sh.worksheet("Penjualan Bisnis")
        return ws_transaksi, ws_bisnis


    def parse_args(text, expected_parts):
        """Helper untuk memecah argumen dengan pemisah '|'.

        Contoh pesan:
        /in 2025-11-17 | gaji | Dana | 1500000 | gaji bulan november

        expected_parts = 5  -> akan mengembalikan list 5 elemen.
        """
        try:
            # buang command (/in, /out, /sale)
            without_command = text.split(" ", 1)[1]
        except IndexError:
            return None

        parts = [p.strip() for p in without_command.split("|")]
        if len(parts) != expected_parts:
            return None
        return parts


    # ================== HANDLER ==================

    def start(update, context):
        msg = (
            "Halo! Saya bot pencatat keuangan pribadi + bisnis.

"
            "Format perintah:

"
            "/in TANGGAL | KATEGORI | KE_AKUN | NOMINAL | DESKRIPSI\n"
            "Contoh:\n"
            "/in 2025-11-17 | gaji | BCA | 5000000 | gaji november\n
"
            "/out TANGGAL | KATEGORI | DARI_AKUN | NOMINAL | DESKRIPSI\n"
            "Contoh:\n"
            "/out 2025-11-18 | makan | Dana | 25000 | nasi goreng\n
"
            "/sale TANGGAL | PRODUK | QTY | HARGA_JUAL_PER_UNIT | MODAL_PER_UNIT | AKUN_TERIMA | AKUN_BAYAR | CATATAN\n"
            "Contoh:\n"
            "/sale 2025-11-19 | kaos hitam | 2 | 75000 | 50000 | Dana | BCA | order ig @abc\n
"
            "Semua akan tercatat di Google Sheets sesuai format."
        )
        update.message.reply_text(msg)


    def cmd_in(update, context):
        """Catat pemasukan (Masuk) ke sheet Transaksi."""
        user_text = update.message.text
        parts = parse_args(user_text, 5)
        if not parts:
            update.message.reply_text(
                "Format salah. Contoh:\n"
                "/in 2025-11-17 | gaji | BCA | 5000000 | gaji november"
            )
            return

        tanggal_str, kategori, ke_akun, nominal_str, deskripsi = parts

        # Validasi tanggal dan nominal
        try:
            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            update.message.reply_text("Format tanggal harus YYYY-MM-DD.")
            return

        try:
            nominal = float(nominal_str)
        except ValueError:
            update.message.reply_text("Nominal harus angka, contoh: 150000 atau 150000.5")
            return

        try:
            ws_transaksi, _ = get_sheets()
            # Struktur: Tanggal, Jenis, Kategori, Dari Akun, Ke Akun, Nominal, Deskripsi
            ws_transaksi.append_row([
                tanggal,
                "Masuk",
                kategori,
                "",          # Dari Akun (kosong, uang masuk dari luar)
                ke_akun,
                nominal,
                deskripsi,
            ])
        except Exception as e:
            logger.error(e)
            update.message.reply_text("Gagal menulis ke Google Sheets.")
            return

        update.message.reply_text(f"Pemasukan dicatat: {kategori} ke {ke_akun} sebesar {nominal}")


    def cmd_out(update, context):
        """Catat pengeluaran (Keluar) ke sheet Transaksi."""
        user_text = update.message.text
        parts = parse_args(user_text, 5)
        if not parts:
            update.message.reply_text(
                "Format salah. Contoh:\n"
                "/out 2025-11-18 | makan | Dana | 25000 | nasi goreng"
            )
            return

        tanggal_str, kategori, dari_akun, nominal_str, deskripsi = parts

        # Validasi tanggal dan nominal
        try:
            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            update.message.reply_text("Format tanggal harus YYYY-MM-DD.")
            return

        try:
            nominal = float(nominal_str)
        except ValueError:
            update.message.reply_text("Nominal harus angka, contoh: 15000 atau 15000.5")
            return

        try:
            ws_transaksi, _ = get_sheets()
            # Struktur: Tanggal, Jenis, Kategori, Dari Akun, Ke Akun, Nominal, Deskripsi
            ws_transaksi.append_row([
                tanggal,
                "Keluar",
                kategori,
                dari_akun,
                "",          # Ke Akun (kosong, uang keluar ke pihak luar)
                nominal,
                deskripsi,
            ])
        except Exception as e:
            logger.error(e)
            update.message.reply_text("Gagal menulis ke Google Sheets.")
            return

        update.message.reply_text(f"Pengeluaran dicatat: {kategori} dari {dari_akun} sebesar {nominal}")


    def cmd_sale(update, context):
        """Catat penjualan bisnis:
        - Masuk ke sheet Penjualan Bisnis (detail jualan + profit)
        - 2 baris ke Transaksi (pemasukan & modal)
        """
        user_text = update.message.text
        parts = parse_args(user_text, 8)
        if not parts:
            update.message.reply_text(
                "Format salah. Contoh:\n"
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

        # Validasi
        try:
            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            update.message.reply_text("Format tanggal harus YYYY-MM-DD.")
            return

        try:
            qty = float(qty_str)
            harga_jual_unit = float(harga_jual_unit_str)
            modal_unit = float(modal_unit_str)
        except ValueError:
            update.message.reply_text("Qty, harga jual, dan modal per unit harus berupa angka.")
            return

        total_jual = qty * harga_jual_unit
        total_modal = qty * modal_unit
        profit = total_jual - total_modal

        try:
            ws_transaksi, ws_bisnis = get_sheets()

            # 1) Tambah ke Penjualan Bisnis
            # Kolom: Tanggal, Produk, Qty, Harga Jual / Unit, Modal / Unit, Keuntungan, Akun Terima, Akun Bayar, Catatan
            ws_bisnis.append_row([
                tanggal,
                produk,
                qty,
                harga_jual_unit,
                modal_unit,
                profit,
                akun_terima,
                akun_bayar,
                catatan,
            ])

            # 2) Tambah ke Transaksi: pemasukan dari customer
            # Tanggal, Jenis, Kategori, Dari Akun, Ke Akun, Nominal, Deskripsi
            ws_transaksi.append_row([
                tanggal,
                "Masuk",
                f"Penjualan {produk}",
                "Customer",
                akun_terima,
                total_jual,
                catatan,
            ])

            # 3) Tambah ke Transaksi: pengeluaran modal ke supplier
            ws_transaksi.append_row([
                tanggal,
                "Keluar",
                f"Modal {produk}",
                akun_bayar,
                "Supplier",
                total_modal,
                catatan,
            ])

        except Exception as e:
            logger.error(e)
            update.message.reply_text("Gagal menulis ke Google Sheets.")
            return

        update.message.reply_text(
            f"Penjualan dicatat. Produk: {produk}, qty: {qty}, profit: {profit}."
        )


    def main():
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
