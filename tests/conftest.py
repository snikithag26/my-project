import os
import tempfile

os.environ["AUTISPHERE_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
