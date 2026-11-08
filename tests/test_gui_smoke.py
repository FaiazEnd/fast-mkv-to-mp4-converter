import pytest
from unittest.mock import patch, MagicMock
from converter.controller import ConversionController

def test_gui_import_and_controller_binding():
    from converter.gui import MainWindow
    controller = ConversionController()
    
    # Verify MainWindow can be instantiated with controller
    with patch("customtkinter.CTk.mainloop"):
        with patch("customtkinter.CTk.update"):
            with patch("customtkinter.CTk.winfo_screenwidth", return_value=1920):
                with patch("customtkinter.CTk.winfo_screenheight", return_value=1080):
                    app = MainWindow(controller=controller)
                    assert app.controller == controller
                    assert hasattr(app, "progress_bar")
                    assert hasattr(app, "format_var")
                    assert hasattr(app, "video_codec_var")
                    assert hasattr(app, "audio_codec_var")
                    app.destroy()
