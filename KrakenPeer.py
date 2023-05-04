import libtorrent as lt
import time
import sys
from PyQt5 import QtWidgets, QtGui, QtCore

class TorrentClient(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Configurar la sesión del cliente torrent
        self.ses = lt.session()
        self.ses.listen_on(6881, 6891)

        # Configurar la barra de progreso
        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setGeometry(10, 10, 300, 25)

        # Configurar el botón para agregar nuevos torrents
        self.add_button = QtWidgets.QPushButton('Agregar Torrent', self)
        self.add_button.setGeometry(10, 50, 100, 25)
        self.add_button.clicked.connect(self.add_torrent)

        # Configurar la ventana principal
        self.setGeometry(300, 300, 320, 100)
        self.setWindowTitle('Cliente Torrent')
        self.show()

    def add_torrent(self):
        # Abrir el cuadro de diálogo para seleccionar el archivo torrent
        file_dialog = QtWidgets.QFileDialog.getOpenFileName(self, 'Seleccionar archivo torrent')
        torrent_file = file_dialog[0]

        # Agregar el torrent a la sesión
        handle = self.ses.add_torrent({'ti': lt.torrent_info(torrent_file), 'save_path': '.'})

        # Monitorear el progreso del torrent
        while (not handle.is_seed()):
            status = handle.status()
            progress = int(status.progress * 100)
            self.progress.setValue(progress)
            QtWidgets.qApp.processEvents()
            time.sleep(1)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    client = TorrentClient()
    sys.exit(app.exec_())