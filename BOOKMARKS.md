### Docs
1. [Dpy Docs](https://discordpy.readthedocs.io/en/latest/)
2. 




*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
*
### Code snippets for future 

(I just dont want to see them in TODO.md)

in the beginning of databse.py
```py
import sys
import oracledb

oracledb.version = "8.3.0"
sys.modules["cx_Oracle"] = oracledb
from config import (
    ORACLE_UN, ORACLE_PW, ORACLE_CS, ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE_NAME
)
```

and replace `self.engine = ` with 
```python
self._engine = create_async_engine(
    f'oracle://{ORACLE_UN}:{ORACLE_PW}@{ORACLE_CS}',  # <- ORACLE_URL
    echo=False,  # echo = true to debug
    connect_args={
        'host': ORACLE_HOST,
        'port': ORACLE_PORT,
        'service_name': ORACLE_SERVICE_NAME
    }
)  # connect to database
```