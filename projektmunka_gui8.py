import sys
import json
import psycopg2
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTableWidget, QPushButton,
    QLabel, QStackedWidget, QFormLayout, QSpinBox, QComboBox, QTableWidgetItem, QRadioButton, QButtonGroup, QSpacerItem,
    QSizePolicy, QMessageBox, QDialog
)
from PySide6.QtGui import QFontDatabase, QFont, QPixmap, QImageReader, QPainter, QColor
from PySide6.QtCore import QSize, Qt
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis, QLineSeries
from psycopg2 import sql


def connect_db():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="postgres"
        )
        return connection
    except psycopg2.Error as e:
        print(f"Hiba az adatbázishoz csatlakozás során: {e}")
        return None


def load_translations():
    with open('translations.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def delete_book(cursor, connection, username, isbn, translations, current_language):
    try:
        permission_query = sql.SQL("""
            SELECT delete_permission FROM user_credentials
            WHERE user_name = %s
        """)
        cursor.execute(permission_query, (username,))
        permission = cursor.fetchone()

        if not permission or not permission[0]:
            error_title = translations.get(current_language, {}).get("permission_error_title")
            error_message = translations.get(current_language, {}).get("permission_error_message")
            QMessageBox.warning(None, error_title, error_message)
            return False

        query = sql.SQL("""
            DELETE FROM books2
            WHERE isbn = %s
        """)
        cursor.execute(query, (isbn,))
        connection.commit()

        return cursor.rowcount > 0

    except (psycopg2.Error, ValueError) as e:
        print("Hiba a könyv törlése során:", e)
        return False


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.username = None

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Felhasználónév")

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Jelszó")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("Bejelentkezés")
        self.register_button = QPushButton("Regisztráció")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Felhasználónév:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Jelszó:"))
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addWidget(self.register_button)

        self.setLayout(layout)

        self.login_button.clicked.connect(self.handle_login)
        self.register_button.clicked.connect(self.open_register_dialog)

        self.login_successful = False

    def handle_login(self):
        connection = connect_db()
        if connection:
            cursor = connection.cursor()

            username = self.username_input.text()
            password = self.password_input.text()

            query = sql.SQL("""
                SELECT * FROM user_credentials
                WHERE user_name = %s AND password = %s
            """)
            cursor.execute(query, (username, password))
            user_data = cursor.fetchone()

            if user_data:
                QMessageBox.information(self, "Sikeres bejelentkezés", "Sikeresen bejelentkeztél!")
                self.username = username
                self.login_successful = True
                self.accept()
            else:
                QMessageBox.warning(self, "Hibás bejelentkezés", "Hibás felhasználónév vagy jelszó!")

            cursor.close()
            connection.close()

    def open_register_dialog(self):
        register_dialog = RegisterDialog(self)
        register_dialog.exec()


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Regisztráció")

        layout = QVBoxLayout()

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Új felhasználónév")

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Jelszó")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Email cím")

        self.dob_input = QLineEdit(self)
        self.dob_input.setPlaceholderText("Születési dátum (YYYY-MM-DD)")

        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText("Telefonszám")

        self.register_button = QPushButton("Regisztráció")

        layout.addWidget(QLabel("Felhasználónév:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Jelszó:"))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Email:"))
        layout.addWidget(self.email_input)
        layout.addWidget(QLabel("Születési dátum:"))
        layout.addWidget(self.dob_input)
        layout.addWidget(QLabel("Telefonszám:"))
        layout.addWidget(self.phone_input)
        layout.addWidget(self.register_button)

        self.setLayout(layout)

        self.register_button.clicked.connect(self.handle_registration)

    def handle_registration(self):
        connection = connect_db()
        if connection:
            cursor = connection.cursor()

            user_name = self.username_input.text()
            password = self.password_input.text()
            email = self.email_input.text()
            date_of_birth = self.dob_input.text()
            phone_number = self.phone_input.text()

            write_permission = True
            edit_permission = True
            delete_permission = False

            query = sql.SQL("""
                INSERT INTO user_credentials (user_name, password, email, date_of_birth, phone_number, write_permission,
                edit_permission, delete_permission)           
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """)

            insert_data = (
                user_name,
                password,
                email,
                date_of_birth,
                phone_number,
                write_permission,
                edit_permission,
                delete_permission
            )

            cursor.execute(query, insert_data)
            connection.commit()

            QMessageBox.information(self, "Sikeres regisztráció", "Sikeresen regisztráltál!")
            cursor.close()
            connection.close()

            self.accept()


def get_books_statistics(cursor):
    try:
        query = "SELECT COUNT(*), SUM(page_num) FROM books2"
        cursor.execute(query)
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        return 0, 0
    except psycopg2.Error as e:
        print(f"Hiba a statisztikák lekérdezése során: {e}")
        return 0, 0


def list_books_by_search(cursor, search_term, search_field):
    try:
        valid_fields = {
            "isbn": "isbn",
            "authors": "authors",
            "title": "title",
            "page_num": "page_num",
            "price": "price",
            "available": "available"
        }

        if search_field not in valid_fields:
            raise ValueError(f"Érvénytelen keresési mező: {search_field}")

        if search_field in ["page_num", "price", "available"]:
            if search_term.strip() == "":
                query = sql.SQL(f"SELECT isbn, authors, title, page_num, price, available FROM books2")
                cursor.execute(query)
            else:
                query = sql.SQL(
                    f"SELECT isbn, authors, title, page_num, price, available FROM books2 WHERE {valid_fields[search_field]} = %s")
                cursor.execute(query, (search_term,))

        elif search_field == "authors":
            query = sql.SQL(
                f"SELECT isbn, authors, title, page_num, price, available FROM books2 WHERE array_to_string(authors, ', ') ILIKE %s")
            cursor.execute(query, (f"%{search_term}%",))

        else:
            query = sql.SQL(
                f"SELECT isbn, authors, title, page_num, price, available FROM books2 WHERE {valid_fields[search_field]} ILIKE %s")
            cursor.execute(query, (f"%{search_term}%",))

        books = cursor.fetchall()
        return books

    except psycopg2.Error as e:
        print(f"Hiba a könyvek lekérdezése során: {e}")
        return []


def confirm_delete_book(self):
    selected_row = self.book_table.currentRow()

    if selected_row == -1:
        QMessageBox.warning(
            self,
            self.get_translation("error"),
            self.get_translation("delete_warning")
        )
        return

    isbn = self.book_table.item(selected_row, 0).text()

    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setText(self.get_translation("delete_confirmation").format(isbn=isbn))
    msg_box.setWindowTitle(self.get_translation("delete_title"))
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

    yes_button = msg_box.button(QMessageBox.Yes)
    no_button = msg_box.button(QMessageBox.No)
    yes_button.setText(self.get_translation("yes"))
    no_button.setText(self.get_translation("no"))

    response = msg_box.exec()

    if response == QMessageBox.Yes:
        connection = connect_db()
        if connection:
            cursor = connection.cursor()

            username = self.logged_in_username
            if self.delete_book(cursor, connection, username, isbn, self.translations, self.current_language):
                success_message = self.translations.get(self.current_language, {}).get("delete_success")
                QMessageBox.information(self, self.get_translation("success_title"), success_message)
                self.refresh_books()
            else:
                error_message = self.translations.get(self.current_language, {}).get("delete_failure")
                QMessageBox.warning(self, self.get_translation("error_title"), error_message)

            cursor.close()
            connection.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.translations = load_translations()
        self.current_language = 'hu'

        self.logged_in_username = None

        self.show_login_dialog()

        self.init_ui()

    def show_login_dialog(self):
        login_dialog = LoginDialog()
        if login_dialog.exec() == QDialog.Accepted and login_dialog.login_successful:
            print("Sikeres bejelentkezés.")
            self.logged_in_username = login_dialog.username
        else:
            sys.exit()

    def init_ui(self):
        self.setWindowTitle("Könyvkezelő")
        self.setGeometry(100, 100, 1080, 640)

        label = QLabel("Üdvözöljük a Könyvkezelőben!", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

        font_id = QFontDatabase.addApplicationFont("TitilliumWeb-Regular.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

        font = QFont(font_family, 11)
        font.setHintingPreference(QFont.PreferNoHinting)
        font.setStyleStrategy(QFont.PreferAntialias)

        app.setFont(font)

        self.setWindowTitle("Könyvkezelő")
        self.setGeometry(100, 100, 1080, 640)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.left_panel = QVBoxLayout()
        self.left_panel.setContentsMargins(0, 0, 0, 0)
        self.left_panel.setSpacing(0)

        left_panel_widget = QWidget()
        left_panel_widget.setStyleSheet("background-color: #116186;")
        left_panel_widget.setLayout(self.left_panel)

        left_panel_widget.setFixedWidth(200)

        main_layout.addWidget(left_panel_widget)

        right_panel_widget = QWidget()
        right_panel_widget.setStyleSheet("background-color: #f9f9f9;")
        main_layout.addWidget(right_panel_widget)

        self.right_panel = QStackedWidget()
        right_panel_widget.setLayout(QVBoxLayout())
        right_panel_widget.layout().addWidget(self.right_panel)

        self.create_pages()
        self.create_buttons()

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.show_query_page()

    def create_price_chart(self, cursor):
        cursor.execute("SELECT title, price FROM books2")
        books = cursor.fetchall()

        books_sorted = sorted(books, key=lambda x: x[1], reverse=True)

        bar_set = QBarSet(self.get_translation("price"))
        bar_set.setColor(QColor("#73bfb2"))

        categories = []
        prices = []

        for book in books_sorted:
            title, price = book
            categories.append(title)
            bar_set.append(price)
            prices.append(price)

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(self.get_translation("book_price_chart_title"))
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsVisible(False)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        max_price = max(prices)
        axis_y = QValueAxis()
        axis_y.setRange(0, max_price)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().hide()

        avg_price = sum(prices) / len(prices) if prices else 0

        avg_line_series = QLineSeries()
        avg_line_series.append(0, avg_price)
        avg_line_series.append(len(categories) - 1, avg_price)
        chart.addSeries(avg_line_series)

        avg_line_series.attachAxis(axis_x)
        avg_line_series.attachAxis(axis_y)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        def draw_avg_price_label(painter):
            painter.save()

            font = QFont("Titillium Web", 10)
            painter.setFont(font)
            painter.setPen(QColor("#105e84"))

            plot_area = chart.plotArea()
            midpoint_x = plot_area.left() + (plot_area.width() / 2)
            y_position = plot_area.top() + (plot_area.bottom() - plot_area.top()) * (1 - avg_price / max_price)

            avg_price_text = self.get_translation("average_price").format(avg_price=avg_price)

            painter.drawText(midpoint_x - 40, y_position - 10, avg_price_text)

            painter.restore()

        def custom_paint_event(event):
            chart_view._old_paintEvent(event)
            painter = QPainter(chart_view.viewport())
            draw_avg_price_label(painter)

        chart_view._old_paintEvent = chart_view.paintEvent
        chart_view.paintEvent = custom_paint_event

        return chart_view

    def create_buttons(self):
        header_layout = QHBoxLayout()

        logo_label = QLabel()

        image_reader = QImageReader("book_logo.png")
        image_reader.setScaledSize(QSize(66, 66))
        book_logo_pixmap = QPixmap.fromImageReader(image_reader)

        logo_label.setPixmap(book_logo_pixmap)

        self.header_label = QLabel(self.get_translation("header_label"))
        self.header_label.setStyleSheet("""
            color: #73bfb2;
            text-transform: uppercase;
            font-size: 11px;
            font-weight: bold;
            padding-left: 10px;
        """)
        self.header_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        header_layout.addWidget(logo_label)
        header_layout.addWidget(self.header_label)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)

        self.left_panel.addWidget(header_widget)

        self.dashboard_button = QPushButton(self.get_translation("dashboard"))
        self.query_button = QPushButton(self.get_translation("query_books"))
        self.add_button = QPushButton(self.get_translation("add_book"))
        self.settings_button = QPushButton(self.get_translation("settings"))

        for button in [self.dashboard_button, self.query_button, self.add_button, self.settings_button]:
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setMinimumHeight(50)
            button.setMaximumWidth(200)

        self.set_button_style(self.dashboard_button)
        self.set_button_style(self.query_button)
        self.set_button_style(self.add_button)
        self.set_button_style(self.settings_button)

        self.dashboard_button.clicked.connect(lambda: self.activate_button(self.dashboard_button))
        self.query_button.clicked.connect(lambda: self.activate_button(self.query_button))
        self.add_button.clicked.connect(lambda: self.activate_button(self.add_button))
        self.settings_button.clicked.connect(lambda: self.activate_button(self.settings_button))

        self.left_panel.addWidget(self.dashboard_button)
        self.left_panel.addSpacing(0)
        self.left_panel.addWidget(self.query_button)
        self.left_panel.addSpacing(0)
        self.left_panel.addWidget(self.add_button)
        self.left_panel.addSpacing(0)
        self.left_panel.addWidget(self.settings_button)

        spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.left_panel.addItem(spacer)

    def set_button_style(self, button, active=False):
        button.setFont(QFont("Titillium Web", 12))

        if active:
            button.setStyleSheet("""
                background-color: #0f5b7d;
                color: white;
                font-weight: bold;
                border: none;
                padding: 10px;
                """)
        else:
            button.setStyleSheet("""
                background-color: #116186;
                color: #65a2be;
                border: none;
                padding: 10px;
                transition: color 1s ease-in-out;
            """)

            button.setStyleSheet("""
                QPushButton:hover {
                    color: white;
                }
                QPushButton {
                    background-color: #116186;
                    color: #65a2be;
                    border: none;
                    padding: 10px;
                    transition: color 1s ease-in-out;
                }
            """)

    def activate_button(self, button):
        self.set_button_style(self.dashboard_button, active=False)
        self.set_button_style(self.query_button, active=False)
        self.set_button_style(self.add_button, active=False)
        self.set_button_style(self.settings_button, active=False)

        self.set_button_style(button, active=True)

        if button == self.dashboard_button:
            self.show_dashboard()
        elif button == self.query_button:
            self.show_query_page()
        elif button == self.add_button:
            self.show_add_page()
        elif button == self.settings_button:
            self.show_settings_page()

    def create_pages(self):
        dashboard_layout = QVBoxLayout()

        self.book_count_label = QLabel("Könyvek száma: Betöltés...")
        self.book_count_label.setAlignment(Qt.AlignCenter)

        self.page_count_label = QLabel("Összes oldalszám: Betöltés...")
        self.page_count_label.setAlignment(Qt.AlignCenter)

        self.book_count_label.setStyleSheet("""
            background-color: #73bfb2;
            border-radius: 15px;
            padding: 15px;
            color: white;
        """)
        self.page_count_label.setStyleSheet("""
            background-color: #b4d4ac;
            border-radius: 15px;
            padding: 15px;
            color: white;
        """)

        dashboard_layout.addWidget(self.book_count_label)
        dashboard_layout.addWidget(self.page_count_label)

        self.chart_widget = QWidget()
        self.chart_layout = QVBoxLayout()
        self.chart_widget.setLayout(self.chart_layout)
        dashboard_layout.addWidget(self.chart_widget)

        dashboard_widget = QWidget()
        dashboard_widget.setLayout(dashboard_layout)
        self.right_panel.addWidget(dashboard_widget)

        self.dashboard_page = dashboard_widget

        self.query_page = self.create_query_page()
        self.modify_page = self.create_modify_page()
        self.right_panel.addWidget(self.query_page)
        self.right_panel.addWidget(self.modify_page)

        self.add_page = self.create_add_page()
        self.right_panel.addWidget(self.add_page)

        self.settings_page = self.create_settings_page()
        self.right_panel.addWidget(self.settings_page)

    def create_modify_page(self):
        modify_layout = QFormLayout()

        self.modify_isbn_input = QLineEdit()
        self.modify_title_input = QLineEdit()
        self.modify_authors_input = QLineEdit()
        self.modify_page_num_input = QSpinBox()
        self.modify_page_num_input.setRange(1, 10000)
        self.modify_price_input = QSpinBox()
        self.modify_price_input.setRange(1, 1000000)
        self.modify_available_input = QSpinBox()
        self.modify_available_input.setRange(0, 1000)

        self.modify_isbn_label = QLabel(self.get_translation("isbn"))
        self.modify_title_label = QLabel(self.get_translation("title"))
        self.modify_authors_label = QLabel(self.get_translation("authors"))
        self.modify_page_num_label = QLabel(self.get_translation("page_count"))
        self.modify_price_label = QLabel(self.get_translation("price"))
        self.modify_available_label = QLabel(self.get_translation("available"))

        modify_layout.addRow(self.modify_isbn_label, self.modify_isbn_input)
        modify_layout.addRow(self.modify_title_label, self.modify_title_input)
        modify_layout.addRow(self.modify_authors_label, self.modify_authors_input)
        modify_layout.addRow(self.modify_page_num_label, self.modify_page_num_input)
        modify_layout.addRow(self.modify_price_label, self.modify_price_input)
        modify_layout.addRow(self.modify_available_label, self.modify_available_input)

        button_layout = QHBoxLayout()

        self.save_changes_button = QPushButton(self.get_translation("save_changes"))
        self.save_changes_button.setStyleSheet("""
            background-color: #73bfb2;
            color: white;
            padding: 10px;
        """)

        self.discard_changes_button = QPushButton(self.get_translation("discard_changes"))
        self.discard_changes_button.setStyleSheet("""
            background-color: #e9577e;
            color: white;
            padding: 10px;
        """)

        button_layout.addWidget(self.save_changes_button)
        button_layout.addWidget(self.discard_changes_button)

        self.save_changes_button.clicked.connect(self.save_book_changes)
        self.discard_changes_button.clicked.connect(self.discard_book_changes)

        modify_layout.addRow(button_layout)

        self.status_label = QLabel("")
        modify_layout.addRow(self.status_label)

        modify_widget = QWidget()
        modify_widget.setLayout(modify_layout)
        return modify_widget

    def save_book_changes(self):
        connection = connect_db()
        if connection:
            cursor = connection.cursor()

            isbn = self.modify_isbn_input.text()
            title = self.modify_title_input.text()
            authors = self.modify_authors_input.text()
            page_num = self.modify_page_num_input.value()
            price = self.modify_price_input.value()
            available = self.modify_available_input.value()

            query = sql.SQL("""
                UPDATE books2
                SET title = %s, authors = %s, page_num = %s, price = %s, available = %s
                WHERE isbn = %s
            """)

            cursor.execute(query, (title, authors.split(', '), page_num, price, available, isbn))
            connection.commit()

            cursor.close()
            connection.close()

            self.clear_modify_inputs()

            self.status_label.setText(self.get_translation("success_message"))

    def discard_book_changes(self):
        self.clear_modify_inputs()
        QMessageBox.information(self, "Elvetve", "A módosítások elvetve.")
        self.show_query_page()

    def clear_modify_inputs(self):
        self.modify_isbn_input.clear()
        self.modify_title_input.clear()
        self.modify_authors_input.clear()
        self.modify_page_num_input.setValue(1)
        self.modify_price_input.setValue(1)
        self.modify_available_input.setValue(0)

    def open_modify_book_page(self):
        selected_row = self.book_table.currentRow()
        if selected_row == -1:
            error_message = self.get_translation("select_book_error")
            QMessageBox.warning(self, self.get_translation("error"), error_message)
            return

        isbn = self.book_table.item(selected_row, 0).text()
        authors = self.book_table.item(selected_row, 1).text()
        title = self.book_table.item(selected_row, 2).text()
        page_num = int(self.book_table.item(selected_row, 3).text())
        price = int(self.book_table.item(selected_row, 4).text())
        available = int(self.book_table.item(selected_row, 5).text())

        self.modify_isbn_input.setText(isbn)
        self.modify_title_input.setText(title)
        self.modify_authors_input.setText(authors)
        self.modify_page_num_input.setValue(page_num)
        self.modify_price_input.setValue(price)
        self.modify_available_input.setValue(available)

        self.right_panel.setCurrentWidget(self.modify_page)

    def show_dashboard(self):
        connection = connect_db()
        if connection:
            cursor = connection.cursor()
            book_count, page_count = get_books_statistics(cursor)

            self.book_count_label.setText(f"{self.get_translation('book_count_label')} {book_count}")
            self.page_count_label.setText(f"{self.get_translation('page_count_label')} {page_count}")

            if self.chart_layout.count() > 0:
                old_chart = self.chart_layout.itemAt(0).widget()
                if old_chart:
                    self.chart_layout.removeWidget(old_chart)
                    old_chart.deleteLater()

            chart_view = self.create_price_chart(cursor)
            self.chart_layout.addWidget(chart_view)

            cursor.close()
            connection.close()

        self.right_panel.setCurrentWidget(self.dashboard_page)
        self.update_translations()

    def show_query_page(self):
        self.right_panel.setCurrentWidget(self.query_page)

    def show_add_page(self):
        self.right_panel.setCurrentWidget(self.add_page)

    def show_settings_page(self):
        self.right_panel.setCurrentWidget(self.settings_page)

    def create_query_page(self):
        query_layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.get_translation("title"))
        self.search_input.returnPressed.connect(self.refresh_books)

        self.refresh_button = QPushButton(self.get_translation("query_books"))

        self.refresh_button.pressed.connect(self.on_refresh_button_pressed)
        self.refresh_button.released.connect(self.on_refresh_button_released)

        self.refresh_button.setStyleSheet("""
               background-color: #73bfb2;
               color: white;
               padding: 10px;
           """)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.refresh_button)
        query_layout.addLayout(search_layout)

        radio_layout = QHBoxLayout()

        self.search_label = QLabel(self.get_translation("search_condition"))
        radio_layout.addWidget(self.search_label)

        self.radio_group = QHBoxLayout()
        self.radio_buttons = QButtonGroup()

        self.isbn_radio = QRadioButton(self.get_translation("isbn"))
        self.author_radio = QRadioButton(self.get_translation("authors"))
        self.title_radio = QRadioButton(self.get_translation("title"))
        self.page_num_radio = QRadioButton(self.get_translation("page_count"))
        self.price_radio = QRadioButton(self.get_translation("price"))
        self.available_radio = QRadioButton(self.get_translation("available"))

        self.title_radio.setChecked(True)

        self.radio_buttons.addButton(self.isbn_radio)
        self.radio_buttons.addButton(self.author_radio)
        self.radio_buttons.addButton(self.title_radio)
        self.radio_buttons.addButton(self.page_num_radio)
        self.radio_buttons.addButton(self.price_radio)
        self.radio_buttons.addButton(self.available_radio)

        self.radio_group.addWidget(self.isbn_radio)
        self.radio_group.addWidget(self.author_radio)
        self.radio_group.addWidget(self.title_radio)
        self.radio_group.addWidget(self.page_num_radio)
        self.radio_group.addWidget(self.price_radio)
        self.radio_group.addWidget(self.available_radio)

        radio_layout.addLayout(self.radio_group)
        query_layout.addLayout(radio_layout)

        self.book_table = QTableWidget()
        self.book_table.setColumnCount(6)
        self.book_table.setHorizontalHeaderLabels([
            self.get_translation("isbn"),
            self.get_translation("authors"),
            self.get_translation("title"),
            self.get_translation("page_count"),
            self.get_translation("price"),
            self.get_translation("available")
        ])
        self.book_table.horizontalHeader().setDefaultSectionSize(120)
        self.book_table.setStyleSheet("border: 1px solid black;")
        self.book_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.book_table.setSelectionMode(QTableWidget.SingleSelection)
        query_layout.addWidget(self.book_table)

        self.delete_button = QPushButton(self.get_translation("delete_book"))
        self.delete_button.setStyleSheet("""
            background-color: #e9577e;
            color: white;
            padding: 10px;
        """)
        self.delete_button.clicked.connect(self.confirm_delete_book)

        self.modify_button = QPushButton(self.get_translation("modify_book"))
        self.modify_button.setStyleSheet("""
            background-color: #73bfb2;
            color: white;
            padding: 10px;
        """)

        self.modify_button.pressed.connect(self.on_modify_button_pressed)
        self.modify_button.released.connect(self.on_modify_button_released)

        self.modify_button.clicked.connect(self.open_modify_book_page)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.modify_button)
        button_layout.addWidget(self.delete_button)

        query_layout.addLayout(button_layout)

        query_widget = QWidget()
        query_widget.setLayout(query_layout)
        return query_widget

    def on_modify_button_pressed(self):
        self.modify_button.setStyleSheet("""
            background-color: #50a38f;
            color: white;
            padding: 10px;
        """)

    def on_modify_button_released(self):
        self.modify_button.setStyleSheet("""
            background-color: #73bfb2;
            color: white;
            padding: 10px;
        """)

    def on_refresh_button_pressed(self):
        self.refresh_button.setStyleSheet("""
            background-color: #50a38f;
            color: white;
            padding: 10px;
        """)

    def on_refresh_button_released(self):
        self.refresh_button.setStyleSheet("""
            background-color: #73bfb2;
            color: white;
            padding: 10px;
        """)

        self.refresh_books()

    def confirm_delete_book(self):
        selected_row = self.book_table.currentRow()

        if selected_row == -1:
            QMessageBox.warning(
                self,
                self.get_translation("error"),
                self.get_translation("delete_warning")
            )
            return

        isbn = self.book_table.item(selected_row, 0).text()

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(self.get_translation("delete_confirmation").format(isbn=isbn))
        msg_box.setWindowTitle(self.get_translation("delete_title"))
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        yes_button = msg_box.button(QMessageBox.Yes)
        no_button = msg_box.button(QMessageBox.No)
        yes_button.setText(self.get_translation("yes"))
        no_button.setText(self.get_translation("no"))

        response = msg_box.exec()

        if response == QMessageBox.Yes:
            connection = connect_db()
            if connection:
                cursor = connection.cursor()

                username = self.logged_in_username
                if delete_book(cursor, connection, username, isbn, self.translations, self.current_language):
                    QMessageBox.information(self, "Siker", "A könyv sikeresen törölve.")
                    self.refresh_books()
                else:
                    QMessageBox.warning(self, "Hiba", "Nem sikerült törölni a könyvet.")
                cursor.close()
                connection.close()

    def create_add_page(self):
        add_layout = QFormLayout()

        self.isbn_input = QLineEdit()
        self.title_input = QLineEdit()
        self.authors_input = QLineEdit()
        self.page_num_input = QSpinBox()
        self.page_num_input.setRange(1, 10000)
        self.price_input = QSpinBox()
        self.price_input.setRange(1, 1000000)
        self.available_input = QSpinBox()
        self.available_input.setRange(0, 1000)

        self.isbn_label = QLabel(self.get_translation("isbn") + ":")
        self.title_label = QLabel(self.get_translation("title") + ":")
        self.authors_label = QLabel(self.get_translation("authors") + ":")
        self.page_num_label = QLabel(self.get_translation("page_count") + ":")
        self.price_label = QLabel(self.get_translation("price") + ":")
        self.available_label = QLabel(self.get_translation("available") + ":")

        add_layout.addRow(self.isbn_label, self.isbn_input)
        add_layout.addRow(self.title_label, self.title_input)
        add_layout.addRow(self.authors_label, self.authors_input)
        add_layout.addRow(self.page_num_label, self.page_num_input)
        add_layout.addRow(self.price_label, self.price_input)
        add_layout.addRow(self.available_label, self.available_input)

        self.submit_button = QPushButton(self.get_translation("add_book"))

        self.submit_button.pressed.connect(self.on_submit_button_pressed)
        self.submit_button.released.connect(self.on_submit_button_released)

        self.submit_button.setStyleSheet("""
            background-color: #73bfb2;
            color: white;
            padding: 10px;
        """)

        add_layout.addWidget(self.submit_button)

        self.add_message = QLabel("")
        add_layout.addWidget(self.add_message)

        add_widget = QWidget()
        add_widget.setLayout(add_layout)
        return add_widget

    def on_submit_button_pressed(self):
        self.submit_button.setStyleSheet("""
            background-color: #50a38f;
            color: white;
            padding: 10px;
        """)

    def on_submit_button_released(self):
        self.submit_button.setStyleSheet("""
            background-color: #73bfb2;
            color: white;
            padding: 10px;
        """)
        self.add_new_book()

    def create_settings_page(self):
        settings_layout = QVBoxLayout()

        language_layout = QHBoxLayout()
        language_layout.setContentsMargins(0, 0, 0, 0)
        language_layout.setSpacing(5)

        self.language_combo = QComboBox()
        self.language_combo.addItem("Magyar", "hu")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Română", "ro")
        self.language_combo.addItem("Řomani", "romani")
        self.language_combo.addItem("Українська", "ukrainian")
        self.language_combo.currentIndexChanged.connect(self.change_language)
        self.language_combo.setFixedWidth(200)

        self.language_label = QLabel(self.get_translation("language"))
        self.language_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combo)

        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #c0c0c0;")

        copyright_label = QLabel("2024 © Rosenberg Mátyás.\nmatyas.rosenberg@gmail.com")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #888;")

        settings_layout.addLayout(language_layout)
        settings_layout.addWidget(divider)
        settings_layout.addWidget(copyright_label)

        settings_widget = QWidget()
        settings_widget.setLayout(settings_layout)
        return settings_widget

    def get_translation(self, key):
        return self.translations.get(self.current_language, {}).get(key, key)

    def change_language(self):
        self.current_language = self.language_combo.currentData()
        self.update_translations()

    def update_translations(self):
        self.dashboard_button.setText(self.get_translation("dashboard"))
        self.query_button.setText(self.get_translation("query_books"))
        self.add_button.setText(self.get_translation("add_book"))
        self.settings_button.setText(self.get_translation("settings"))

        self.isbn_radio.setText(self.get_translation("isbn"))
        self.author_radio.setText(self.get_translation("authors"))
        self.title_radio.setText(self.get_translation("title"))
        self.page_num_radio.setText(self.get_translation("page_count"))
        self.price_radio.setText(self.get_translation("price"))
        self.available_radio.setText(self.get_translation("available"))

        self.search_input.setPlaceholderText(self.get_translation("title"))
        self.book_table.setHorizontalHeaderLabels([
            self.get_translation("isbn"),
            self.get_translation("authors"),
            self.get_translation("title"),
            self.get_translation("page_count"),
            self.get_translation("price"),
            self.get_translation("available")
        ])
        self.refresh_button.setText(self.get_translation("query_books"))

        self.isbn_label.setText(self.get_translation("isbn") + ":")
        self.title_label.setText(self.get_translation("title") + ":")
        self.authors_label.setText(self.get_translation("authors") + ":")
        self.page_num_label.setText(self.get_translation("page_count") + ":")
        self.price_label.setText(self.get_translation("price") + ":")
        self.available_label.setText(self.get_translation("available") + ":")
        self.submit_button.setText(self.get_translation("add_book"))

        self.search_label.setText(self.get_translation("search_condition"))

        self.delete_button.setText(self.get_translation("delete_book"))

        self.header_label.setText(self.get_translation("header_label"))

        self.modify_isbn_label.setText(self.get_translation("isbn") + ":")
        self.modify_title_label.setText(self.get_translation("title") + ":")
        self.modify_authors_label.setText(self.get_translation("authors") + ":")
        self.modify_page_num_label.setText(self.get_translation("page_count") + ":")
        self.modify_price_label.setText(self.get_translation("price") + ":")
        self.modify_available_label.setText(self.get_translation("available") + ":")

        self.save_changes_button.setText(self.get_translation("save_changes"))
        self.discard_changes_button.setText(self.get_translation("discard_changes"))

        self.modify_button.setText(self.get_translation("modify_book"))

        self.language_label.setText(self.get_translation("language"))

    def refresh_books(self):
        try:
            connection = connect_db()
            if connection is None:
                return

            cursor = connection.cursor()

            search_term = self.search_input.text()

            if self.isbn_radio.isChecked():
                search_field = "isbn"
            elif self.author_radio.isChecked():
                search_field = "authors"
            elif self.page_num_radio.isChecked():
                search_field = "page_num"
            elif self.price_radio.isChecked():
                search_field = "price"
            elif self.available_radio.isChecked():
                search_field = "available"
            else:
                search_field = "title"

            books = list_books_by_search(cursor, search_term, search_field)

            self.book_table.setRowCount(0)
            for row_num, book in enumerate(books):
                isbn, authors, title, page_num, price, available = book
                authors_str = ', '.join(authors) if isinstance(authors, list) else authors
                self.book_table.insertRow(row_num)
                self.book_table.setItem(row_num, 0, QTableWidgetItem(isbn))
                self.book_table.setItem(row_num, 1, QTableWidgetItem(authors_str))
                self.book_table.setItem(row_num, 2, QTableWidgetItem(title))
                self.book_table.setItem(row_num, 3, QTableWidgetItem(str(page_num)))
                self.book_table.setItem(row_num, 4, QTableWidgetItem(str(price)))
                self.book_table.setItem(row_num, 5, QTableWidgetItem(str(available)))

            cursor.close()
            connection.close()
        except Exception as e:
            print(f"Hiba történt a könyvek lekérdezésekor: {e}")

    def add_new_book(self):
        try:
            connection = connect_db()
            if connection is None:
                print("Nem sikerült csatlakozni az adatbázishoz.")
                return

            cursor = connection.cursor()

            isbn = self.isbn_input.text()
            title = self.title_input.text()
            authors = self.authors_input.text()
            page_num = self.page_num_input.value()
            price = self.price_input.value()
            available = self.available_input.value()

            if not isbn or not title or not authors or page_num <= 0 or price <= 0 or available < 0:
                self.add_message.setText(self.get_translation("add_error"))
                return

            authors_list = authors.split(', ')
            query = sql.SQL("""
                INSERT INTO books2 (isbn, title, authors, page_num, price, available)
                VALUES (%s, %s, %s, %s, %s, %s)
            """)
            insert_data = (isbn, title, authors_list, page_num, price, available)
            cursor.execute(query, insert_data)
            connection.commit()

            self.add_message.setText(self.get_translation("add_success"))
            cursor.close()
            connection.close()

        except Exception as e:
            print(f"Hiba a könyv hozzáadása során: {e}")
            self.add_message.setText(self.get_translation("add_error"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
