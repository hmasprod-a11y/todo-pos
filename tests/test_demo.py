import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"todo"))
from services.demo import launcher_path,launch_demo

class DemoLauncherTests(unittest.TestCase):
    def test_launcher_is_resolved_inside_application_root(self):
        with TemporaryDirectory() as tmp,patch("services.demo._app_root",return_value=Path(tmp)):
            self.assertEqual(launcher_path(),Path(tmp)/"TEST_TODO.bat")
            with self.assertRaises(FileNotFoundError):launch_demo()
    def test_windows_launches_only_the_isolated_demo_batch(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"TEST_TODO.bat";path.write_text("@echo off",encoding="ascii")
            with patch("services.demo._app_root",return_value=Path(tmp)),patch("services.demo.os.name","nt"),patch("services.demo.subprocess.Popen") as popen:
                launch_demo()
                popen.assert_called_once_with(["cmd","/c",str(path)],cwd=str(path.parent))
if __name__=="__main__":unittest.main()
