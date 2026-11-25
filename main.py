import sys
import sqlite3
import csv
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem, QLabel,
    QInputDialog, QMessageBox, QFrame, QFileDialog, QStatusBar,
    QMenu, QSplitter, QSlider, QStyle, QDialog, QComboBox
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QAction, QColor, QFont, QPixmap


class DatabaseManager:
    def __init__(self):
        self.db_stations = "stations.db"
        self.db_users = "users.db"
        self.init_databases()

    def init_databases(self):
        with sqlite3.connect(self.db_stations) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS genres (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            cursor.execute("SELECT count(*) FROM genres")
            if cursor.fetchone()[0] == 0:
                base_genres = [
                    "Pop", "Rock", "Dance", "Club", 
                    "Chillout", "Jazz", "News"
                ]
                cursor.executemany(
                    "INSERT INTO genres (name) VALUES (?)",
                    [(g,) for g in base_genres]
                )

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    genre TEXT,
                    user_id INTEGER DEFAULT NULL,
                    is_favorite INTEGER DEFAULT 0
                )
            """)
            conn.commit()

        with sqlite3.connect(self.db_users) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    volume INTEGER DEFAULT 70
                )
            """)
            conn.commit()

    def get_all_genres(self):
        with sqlite3.connect(self.db_stations) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM genres ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def add_genre(self, genre_name):
        try:
            with sqlite3.connect(self.db_stations) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO genres (name) VALUES (?)",
                    (genre_name,)
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_stations(self, user_id=None, filter_fav=False):
        with sqlite3.connect(self.db_stations) as conn:
            cursor = conn.cursor()
            query = (
                "SELECT id, name, url, genre, is_favorite "
                "FROM stations WHERE 1=1"
            )
            params = []
            
            if user_id is not None:
                query += " AND (user_id = ? OR user_id IS NULL)"
                params.append(user_id)
            else:
                query += " AND user_id IS NULL"
                
            if filter_fav:
                query += " AND is_favorite = 1"
                
            cursor.execute(query, params)
            return cursor.fetchall()

    def add_station(self, name, url, genre, user_id=None):
        with sqlite3.connect(self.db_stations) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stations (name, url, genre, user_id) "
                "VALUES (?, ?, ?, ?)",
                (name, url, genre, user_id)
            )
            conn.commit()

    def toggle_favorite(self, station_id, current_status):
        new_status = 0 if current_status == 1 else 1
        with sqlite3.connect(self.db_stations) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE stations SET is_favorite = ? WHERE id = ?",
                (new_status, station_id)
            )
            conn.commit()

    def delete_station(self, station_id):
        with sqlite3.connect(self.db_stations) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM stations WHERE id = ?",
                (station_id,)
            )
            conn.commit()

    def export_to_csv(self, filename, user_id=None):
        stations = self.get_stations(user_id=user_id)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['ID', 'Name', 'URL', 'Genre', 'Favorite']
            )
            writer.writerows(stations)

    def import_from_csv(self, filename, user_id=None):
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 3:
                    name = row[1]
                    url = row[2]
                    genre = row[3] if len(row) >= 4 else "Без жанра"
                    self.add_station(name, url, genre, user_id)

    def create_user(self, username):
        try:
            with sqlite3.connect(self.db_users) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    (username,)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_user_id(self, username):
        with sqlite3.connect(self.db_users) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def get_user_volume(self, user_id):
        with sqlite3.connect(self.db_users) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT volume FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else 70

    def set_user_volume(self, user_id, volume):
        with sqlite3.connect(self.db_users) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET volume = ? WHERE id = ?",
                (volume, user_id)
            )
            conn.commit()


class AddStationDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("Добавить станцию")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Название станции:"))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Например: Radio Record")
        layout.addWidget(self.input_name)

        layout.addWidget(QLabel("URL потока:"))
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("https://example.com/stream.mp3")
        layout.addWidget(self.input_url)

        layout.addWidget(QLabel("Жанр:"))
        genre_layout = QHBoxLayout()
        
        self.combo_genre = QComboBox()
        self.update_genre_list()
        
        btn_add_genre = QPushButton("➕ Новый жанр")
        btn_add_genre.setFixedWidth(120)
        btn_add_genre.clicked.connect(self.create_new_genre)
        
        genre_layout.addWidget(self.combo_genre)
        genre_layout.addWidget(btn_add_genre)
        layout.addLayout(genre_layout)

        btns = QHBoxLayout()
        self.btn_ok = QPushButton("✔ Добавить")
        self.btn_ok.clicked.connect(self.validate_and_accept)
        self.btn_cancel = QPushButton("✖ Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

    def update_genre_list(self):
        current_text = self.combo_genre.currentText()
        self.combo_genre.clear()
        self.combo_genre.addItems(self.db.get_all_genres())
        if current_text:
            self.combo_genre.setCurrentText(current_text)

    def create_new_genre(self):
        text, ok = QInputDialog.getText(
            self, "Новый жанр", "Введите название жанра:"
        )
        if ok and text.strip():
            success = self.db.add_genre(text.strip())
            if success:
                self.update_genre_list()
                self.combo_genre.setCurrentText(text.strip())
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Такой жанр уже существует."
                )

    def validate_and_accept(self):
        if not self.input_name.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название.")
            return
        if not self.input_url.text().strip().startswith("http"):
            QMessageBox.warning(
                self, "Ошибка", 
                "URL должен начинаться с http:// или https://"
            )
            return
        if not self.combo_genre.currentText().strip():
            QMessageBox.warning(
                self, "Ошибка", "Выберите или создайте жанр."
            )
            return
        self.accept()

    def get_data(self):
        return (
            self.input_name.text().strip(),
            self.input_url.text().strip(),
            self.combo_genre.currentText().strip()
        )


class RadioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_user_id = None
        self.current_station_name = None
        self.bg_pixmap = None

        bg_path = "background.jpg"
        if os.path.exists(bg_path):
            self.bg_pixmap = QPixmap(bg_path)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(
            self.on_media_status_changed
        )

        self.init_ui()
        self.apply_styles()
        self.force_login_on_startup()
        self.load_stations()
        self.load_volume_from_db()

    def force_login_on_startup(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Вход")
        msg.setText(
            "Добро пожаловать!\n"
            "Войдите в профиль, чтобы добавлять свои станции, "
            "или продолжите как Гость."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Ok | 
            QMessageBox.StandardButton.Cancel
        )
        msg.button(QMessageBox.StandardButton.Ok).setText("Войти")
        msg.button(QMessageBox.StandardButton.Cancel).setText("Гость")
        
        if msg.exec() == QMessageBox.StandardButton.Ok:
            self.login_user(force=True)

    def init_ui(self):
        self.setWindowTitle("PyQt6 Radio Player")
        self.resize(1050, 720)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)

        profile_layout = QHBoxLayout()
        self.lbl_profile = QLabel("👤 Гость")
        self.lbl_profile.setStyleSheet(
            "font-weight: bold; font-size: 14px;"
        )
        btn_login = QPushButton("Войти")
        btn_login.clicked.connect(
            lambda: self.login_user(force=False)
        )
        btn_logout = QPushButton("Выйти")
        btn_logout.clicked.connect(self.logout_user)
        profile_layout.addWidget(self.lbl_profile)
        profile_layout.addWidget(btn_login)
        profile_layout.addWidget(btn_logout)
        left_layout.addLayout(profile_layout)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск станции...")
        self.search_input.textChanged.connect(self.filter_stations)
        left_layout.addWidget(self.search_input)

        self.station_list = QListWidget()
        self.station_list.itemDoubleClicked.connect(
            self.play_selected_station
        )
        self.station_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.station_list.customContextMenuRequested.connect(
            self.show_context_menu
        )
        left_layout.addWidget(self.station_list)

        btn_add = QPushButton("➕ Добавить станцию")
        btn_add.clicked.connect(self.add_station_dialog)
        
        btn_export = QPushButton("📤 Экспорт в CSV")
        btn_export.clicked.connect(self.export_csv)
        
        btn_import = QPushButton("📥 Импорт из CSV")
        btn_import.clicked.connect(self.import_csv)

        left_layout.addWidget(btn_add)
        left_layout.addWidget(btn_export)
        left_layout.addWidget(btn_import)

        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)

        self.lbl_current_station = QLabel("Выберите станцию")
        self.lbl_current_station.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.lbl_current_station.setStyleSheet(
            "font-size: 36px; font-weight: bold; "
            "margin: 20px; color: #ffffff;"
        )

        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setFixedSize(150, 60)
        self.btn_play.setStyleSheet("font-size: 18px;")
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setFixedSize(150, 60)
        self.btn_stop.setStyleSheet("font-size: 18px;")
        self.btn_stop.clicked.connect(self.stop_playback)

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_stop)

        volume_layout = QHBoxLayout()
        volume_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_volume_icon = QLabel()
        icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaVolume
        )
        self.lbl_volume_icon.setPixmap(icon.pixmap(QSize(32, 32)))

        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70)
        self.slider_volume.setFixedWidth(300)
        self.slider_volume.valueChanged.connect(self.change_volume)

        self.lbl_volume_value = QLabel("70%")
        self.lbl_volume_value.setFixedWidth(50)
        self.lbl_volume_value.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        volume_layout.addWidget(self.lbl_volume_icon)
        volume_layout.addWidget(self.slider_volume)
        volume_layout.addWidget(self.lbl_volume_value)

        right_layout.addStretch(1)
        right_layout.addWidget(self.lbl_current_station)
        right_layout.addSpacing(30)
        right_layout.addLayout(controls_layout)
        right_layout.addSpacing(30)
        right_layout.addLayout(volume_layout)
        right_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 650])
        main_layout.addWidget(splitter)

        self.setStatusBar(QStatusBar())

        self.bg_label = QLabel(central_widget)
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        self.bg_label.lower()
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            self.bg_label.setPixmap(self.bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
            self.bg_label.setScaledContents(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'bg_label') and self.bg_label:
            self.bg_label.setGeometry(
                0, 0, self.width(), self.height()
            )
            if self.bg_pixmap and not self.bg_pixmap.isNull():
                self.bg_label.setPixmap(self.bg_pixmap.scaled(
                    self.size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))

    def apply_styles(self):
        style_sheet = """
        QWidget#centralWidget { background-color: transparent; }
        QWidget {
            color: #e0e0e0;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            background-color: transparent;
        }
        QDialog { background-color: #1e1e24; }
        
        QFrame#leftPanel {
            background-color: rgba(25, 25, 30, 180); 
            border: 1px solid #333;
            border-radius: 10px;
        }
        QFrame#rightPanel {
            background-color: rgba(25, 25, 30, 180);
            border: 1px solid #333;
            border-radius: 10px;
        }
        
        QListWidget {
            background-color: rgba(15, 15, 20, 150);
            border: 1px solid #444;
            border-radius: 6px;
            padding: 5px;
            font-size: 15px;
        }
        QListWidget::item {
            padding: 10px;
            border-bottom: 1px solid #333;
        }
        QListWidget::item:selected {
            background-color: #4a6fa5;
            color: #fff;
        }
        QListWidget::item:hover {
            background-color: rgba(255, 255, 255, 20);
        }
        
        QPushButton {
            background-color: rgba(44, 44, 52, 180);
            border: 1px solid #4a4a55;
            border-radius: 6px;
            padding: 8px 12px;
            color: #eee;
        }
        QPushButton:hover {
            background-color: rgba(58, 58, 69, 200);
            border: 1px solid #6a6a80;
        }
        QPushButton:pressed { background-color: #1e1e24; }
        
        QLineEdit {
            background-color: rgba(42, 42, 50, 180);
            border: 1px solid #555;
            border-radius: 6px;
            padding: 7px;
            color: #ffffff;
        }
        
        QComboBox {
            background-color: #2a2a32;
            border: 1px solid #555;
            border-radius: 6px;
            padding: 5px;
            color: #ffffff;
        }
        QComboBox:focus {
            border: 1px solid #4a6fa5;
        }
        QComboBox QAbstractItemView {
            background-color: #2a2a32;
            color: #ffffff;
            selection-background-color: #4a6fa5;
            selection-color: #ffffff;
            border: 1px solid #555;
        }
        
        QSlider::groove:horizontal {
            height: 8px;
            background: #333;
            border-radius: 4px;
        }
        QSlider::sub-page:horizontal {
            background: #4a6fa5;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #ddd;
            width: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }
        QSlider::handle:horizontal:hover { background: #fff; }
        QLabel { color: #e8e8e8; }
        QStatusBar {
            background-color: rgba(20, 20, 25, 200);
            color: #bbb;
        }
        """
        self.setStyleSheet(style_sheet)

    def login_user(self, force=False):
        text, ok = QInputDialog.getText(
            self, "Профиль", "Введите имя пользователя:"
        )
        if ok and text.strip():
            text = text.strip()
            user_id = self.db.get_user_id(text)
            if user_id is None:
                user_id = self.db.create_user(text)
                if user_id:
                    QMessageBox.information(
                        self, "Успех", f"Профиль {text} создан!"
                    )
                else:
                    QMessageBox.warning(
                        self, "Ошибка", "Не удалось создать профиль."
                    )
                    return
            else:
                if not force:
                    QMessageBox.information(
                        self, "Успех", f"С возвращением, {text}!"
                    )
            
            self.current_user_id = user_id
            self.lbl_profile.setText(f"👤 {text}")
            self.load_volume_from_db()
            self.load_stations()
        else:
            if not force:
                self.logout_user()

    def logout_user(self):
        self.current_user_id = None
        self.lbl_profile.setText("👤 Гость")
        self.slider_volume.setValue(70)
        self.load_stations()

    def load_stations(self):
        self.station_list.clear()
        stations = self.db.get_stations(user_id=self.current_user_id)
        
        for st in stations:
            item = QListWidgetItem()
            display = st[1]
            if st[4] == 1:
                display = f"★ {st[1]}"
            
            item.setText(f"{display}   [{st[3]}]")
            item.setToolTip(f"Жанр: {st[3]}\nURL: {st[2]}")
            
            item.setData(Qt.ItemDataRole.UserRole, st[0])
            item.setData(Qt.ItemDataRole.UserRole + 1, st[2])
            item.setData(Qt.ItemDataRole.UserRole + 2, st[4])
            item.setData(Qt.ItemDataRole.UserRole + 3, st[3])
            item.setData(Qt.ItemDataRole.UserRole + 4, st[1])
            
            if st[4] == 1:
                item.setForeground(QColor("gold"))
            self.station_list.addItem(item)

    def filter_stations(self):
        text = self.search_input.text().lower()
        for i in range(self.station_list.count()):
            item = self.station_list.item(i)
            item.setHidden(text not in item.text().lower())

    def add_station_dialog(self):
        dialog = AddStationDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, url, genre = dialog.get_data()
            self.db.add_station(
                name, url, genre, user_id=self.current_user_id
            )
            self.load_stations()
            self.statusBar().showMessage(
                f"Добавлена станция: {name}"
            )

    def show_context_menu(self, pos):
        item = self.station_list.itemAt(pos)
        if not item: 
            return
        
        menu = QMenu()
        action_play = QAction("▶ Воспроизвести", self)
        action_play.triggered.connect(
            lambda: self.play_selected_station(item)
        )
        
        action_fav = QAction("★ В избранное / Убрать", self)
        action_fav.triggered.connect(lambda: self.toggle_fav(item))
        
        action_del = QAction("🗑 Удалить станцию", self)
        action_del.triggered.connect(
            lambda: self.delete_station(item)
        )

        menu.addAction(action_play)
        menu.addAction(action_fav)
        menu.addSeparator()
        menu.addAction(action_del)
        menu.exec(self.station_list.mapToGlobal(pos))

    def toggle_fav(self, item):
        st_id = item.data(Qt.ItemDataRole.UserRole)
        current_fav = item.data(Qt.ItemDataRole.UserRole + 2)
        self.db.toggle_favorite(st_id, current_fav)
        self.load_stations()

    def delete_station(self, item):
        st_id = item.data(Qt.ItemDataRole.UserRole)
        clean_name = item.data(Qt.ItemDataRole.UserRole + 4)
        reply = QMessageBox.question(
            self, "Удаление", 
            f"Удалить станцию '{clean_name}'?",
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_station(st_id)
            self.load_stations()

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить CSV", "", "CSV Files (*.csv)"
        )
        if path:
            self.db.export_to_csv(path, user_id=self.current_user_id)
            QMessageBox.information(
                self, "Экспорт", "Станции сохранены."
            )

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть CSV", "", "CSV Files (*.csv)"
        )
        if path:
            try:
                self.db.import_from_csv(
                    path, user_id=self.current_user_id
                )
                self.load_stations()
                QMessageBox.information(
                    self, "Импорт", "Станции загружены."
                )
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)
        self.lbl_volume_value.setText(f"{value}%")
        if self.current_user_id:
            self.db.set_user_volume(self.current_user_id, value)

    def load_volume_from_db(self):
        if self.current_user_id:
            vol = self.db.get_user_volume(self.current_user_id)
        else:
            vol = 70
        self.slider_volume.setValue(vol)
        self.audio_output.setVolume(vol / 100.0)
        self.lbl_volume_value.setText(f"{vol}%")

    def play_selected_station(self, item):
        url = item.data(Qt.ItemDataRole.UserRole + 1)
        name = item.data(Qt.ItemDataRole.UserRole + 4)
        genre = item.data(Qt.ItemDataRole.UserRole + 3)
        
        self.current_station_name = name
        self.lbl_current_station.setText(f"{name}\n{genre}")
        
        self.player.setSource(QUrl(url))
        self.player.play()
        self.btn_play.setText("⏸ Pause")
        self.statusBar().showMessage(f"Играет: {name} [{genre}]")

    def toggle_play(self):
        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶ Play")
        else:
            self.player.play()
            self.btn_play.setText("⏸ Pause")

    def stop_playback(self):
        self.player.stop()
        self.btn_play.setText("▶ Play")
        self.lbl_current_station.setText("Остановлено")
        self.current_station_name = None

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop_playback()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.statusBar().showMessage(
                "Ошибка: Неверная ссылка или формат."
            )
            self.stop_playback()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = RadioApp()
    window.show()
    sys.exit(app.exec())