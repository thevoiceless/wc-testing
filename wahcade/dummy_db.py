from dummy_cursor import DummyCursor

class DummyDB:
    def cursor(self):
        return DummyCursor()
