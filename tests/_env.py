"""One data folder for the whole test process. Imported by every test module before gemini_app:
the coordinator and the engines it starts must read the same store, whichever module loads first."""
import atexit
import os
import pathlib
import shutil
import tempfile

if 'SOL83_TEST_HOME' not in os.environ:
    _home = tempfile.mkdtemp(prefix='sol83-tests-')
    os.environ['SOL83_TEST_HOME'] = _home
    atexit.register(shutil.rmtree, _home, True)
HOME = pathlib.Path(os.environ['SOL83_TEST_HOME'])
os.environ['GEMINI_HOME'] = str(HOME)
os.environ.pop('SOL83_HOME', None)
os.environ['GEMINI_NOTIFY'] = '0'
