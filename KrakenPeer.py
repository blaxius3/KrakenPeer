import libtorrent as lt
import time
import sys
from PyQt5 import QtWidgets, QtGui, QtCore


class TorrentWidgetItem(QtWidgets.QWidget):
    remove_torrent = QtCore.pyqtSignal(dict)

    def __init__(self, torrent, session, parent=None):
        super(TorrentWidgetItem, self).__init__(parent)

        self.torrent = torrent
        self.session = session

        layout = QtWidgets.QHBoxLayout(self)

        self.name_label = QtWidgets.QLabel(self.torrent['name'])
        layout.addWidget(self.name_label)

        self.pause_button = QtWidgets.QPushButton('Pausar', self)
        self.pause_button.clicked.connect(self.pause_resume)
        layout.addWidget(self.pause_button)

        self.remove_button = QtWidgets.QPushButton('Eliminar', self)
        self.remove_button.clicked.connect(self.remove)
        layout.addWidget(self.remove_button)

    def update_status(self, status_text):
        self.name_label.setText(status_text)

    def pause_resume(self):
        if self.torrent['handle'].status().paused:
            self.torrent['handle'].resume()
            self.pause_button.setText('Pausar')
        else:
            self.torrent['handle'].pause()
            self.pause_button.setText('Reanudar')

    def remove(self):
        self.torrent['handle'].pause()
        self.torrent['to_remove'] = True
        self.setParent(None)
        self.session.remove_torrent(self.torrent['handle'])
        self.remove_torrent.emit(self.torrent)


class TorrentClient(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.upload_limit = None
        self.download_limit = None

        self.torrents = []

        self.setGeometry(300, 300, 400, 400)
        self.setWindowIcon(QtGui.QIcon('img/1.ico'))
        self.setWindowTitle('KrakenPeer')

        style = '''
            QWidget {
                background-color: #222;
                color: #fff;
            }
            QPushButton {
                background-color: #444;
                color: #fff;
            }
            QListWidget {
                background-color: #333;
                color: #fff;
            }
            QListWidget::item:hover {
                background-color: #555;
            }
            QListWidget::item:selected:hover {
                background-color: #666;
            }
            QListWidget::item:selected:active {
                background-color: #777;
            }
        '''
        self.setStyleSheet(style)

        menu_bar = self.menuBar()

        archivo_menu = menu_bar.addMenu('Archivo')

        agregar_torrent_action = QtWidgets.QAction('Agregar Torrent', self)
        agregar_torrent_action.triggered.connect(self.add_torrent)
        archivo_menu.addAction(agregar_torrent_action)

        seleccionar_ruta_action = QtWidgets.QAction('Seleccionar Ruta de Descarga', self)
        seleccionar_ruta_action.triggered.connect(self.select_download_path)
        archivo_menu.addAction(seleccionar_ruta_action)

        download_menu = menu_bar.addMenu('Descarga')

        download_limit_action = QtWidgets.QAction('Límite de descarga', self)
        download_limit_action.triggered.connect(self.set_download_rate_limit_dialog)
        download_menu.addAction(download_limit_action)

        self.torrent_list = QtWidgets.QListWidget(self)
        self.setCentralWidget(self.torrent_list)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_torrents)
        self.timer.start(1000)

        self.download_path = '.'

        self.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.torrent_list.setGeometry(10, 50, self.width() - 20, self.height() - 100)

    def select_download_path(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ShowDirsOnly
        download_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar Ruta de Descarga', self.download_path, options=options)
        if download_path:
            self.download_path = download_path

    def add_torrent(self):
        file_dialog = QtWidgets.QFileDialog.getOpenFileName(self, 'Seleccionar archivo torrent')

        if file_dialog[0]:
            torrent_file = file_dialog[0]

            handle = self.session.add_torrent({'ti': lt.torrent_info(torrent_file), 'save_path': self.download_path})

            self.torrents.append({'handle': handle, 'progress': 0, 'item': None, 'to_remove': False, 'name': handle.name()})

    def update_torrents(self):
        for t in self.torrents:
            if t['to_remove']:
                continue

            handle = t['handle']

            if handle.is_valid():
                status = handle.status()

                if status.paused:
                    continue

                t['progress'] = int(status.progress * 100)
                t['download_rate'] = status.download_rate / 1000

                if not t['item']:
                    t['item'] = TorrentWidgetItem(t, self.session)
                    item_container = QtWidgets.QListWidgetItem()
                    item_container.setSizeHint(t['item'].sizeHint())
                    self.torrent_list.addItem(item_container)
                    self.torrent_list.setItemWidget(item_container, t['item'])
                    t['item'].remove_torrent.connect(self.remove_torrent)
                    t['list_item'] = item_container

                t['item'].update_status(f"{t['name']} - {t['progress']}% - {t['download_rate']} KB/s")

            else:
                self.torrent_list.takeItem(self.torrent_list.row(t['list_item']))
                self.torrents.remove(t)
                break

    def remove_torrent(self, torrent):
        if torrent in self.torrents:
            self.torrent_list.takeItem(self.torrent_list.row(torrent['list_item']))
            self.torrents.remove(torrent)

    def set_download_rate_limit(self, limit):
        if self.download_limit != limit:
            self.download_limit = limit
            self.session.set_download_rate_limit(limit * 1000)

    def set_download_rate_limit_dialog(self):
        limit, ok = QtWidgets.QInputDialog.getInt(self, 'Límite de descarga', 'Velocidad de descarga (KB/s):', self.download_limit or 0, 0)
        if ok:
            self.set_download_rate_limit(limit)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    client = TorrentClient()
    sys.exit(app.exec_())