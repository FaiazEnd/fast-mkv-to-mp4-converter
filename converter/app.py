"""Application entry point for MKV to MP4 Converter."""

import sys
from converter.gui import MainWindow


def run():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    run()
