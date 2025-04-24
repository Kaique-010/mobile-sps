# core/threadlocals.py
import threading
_thread_locals = threading.local()

def get_db_for_thread():
    return getattr(_thread_locals, 'db', 'default')

def set_db_for_thread(db_name):
    _thread_locals.db = db_name
