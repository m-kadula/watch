from pathlib import Path

from .access import DBAccess, DBContext, DBWrapper
from .exceptions import ORMError, OperationError, ConstraintError
from .users import UserRecord, TokenRecord, NewUser, ExistingUser, NewToken, ExistingToken
from .watches import WatchRecord, LogRecord, NewWatch, ExistingWatch, NewLog, ExistingLog


schema_root = (Path(__file__).parent / 'schema').resolve()
schema_files = schema_root / 'user.sql', schema_root / 'watch.sql'

__all__ = (
    'schema_root', 'schema_files',
    'DBAccess', 'DBContext', 'DBWrapper',
    'ORMError', 'ConstraintError', 'OperationError',
    'UserRecord', 'TokenRecord', 'NewUser', 'ExistingUser', 'NewToken', 'ExistingToken',
    'WatchRecord', 'LogRecord', 'NewWatch', 'ExistingWatch', 'NewLog', 'ExistingLog'
)
