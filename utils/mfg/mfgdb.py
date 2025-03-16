import json
import logging
from pathlib import *

logger = logging.getLogger(__name__)

class DummyDb():
    def __init__(self):
        pass
    
    def event(self, sn, bundle):
        print(f"DB WRITE: {sn}: {json.dumps(bundle)}")
    
    def has_event(self, sn, event_type):
        if event_type == "pass":
            return sn == "X1P-DMY-A00-0002"
        if event_type == "print_label":
            return sn < "X1P-DMY-A00-0020"
        return False
    
    def first_without_event(self, board_type, event_type):
        if event_type == "pass":
            return f"{board_type}-0003"
        if event_type == "print_label":
            return f"{board_type}-0020"
        return "{board_type}-0001"

class FlatFileDb():
    def __init__(self, path):
        self.path = Path(path).resolve()
        if not self.path.exists():
            logger.info(f"creating {self.path}")
            self.path.mkdir(0o755)
        if not self.path.is_dir():
            logger.error(f"path {self.path} exists but is not a directory, giving up")
            raise FileExistsError(self.path)
        logger.debug(f"using database in {self.path}")
    
    def _boarddir(self, board_type):
        p = self.path / board_type
        if not p.exists():
            logger.info("creating {p}")
            p.mkdir(0o755)
        if not p.is_dir():
            logger.error("{p} exists but is not a directory, giving up")
            raise FileExistsError(p)
        return p
    
    def event(self, sn, bundle):
        board_type,sn = sn.rsplit("-", 1)
        p = self._boarddir(board_type) / sn

        with p.open("at") as f:
            f.write(json.dumps(bundle) + "\n")
    
    def has_event(self, sn, event_type):
        board_type,sn = sn.rsplit("-", 1)
        p = self._boarddir(board_type) / sn
        
        if not p.exists():
            return False
        with p.open("rt") as f:
            for l in f.readlines():
                j = json.loads(l)
                if j['type'] == event_type:
                    return True
        
        return False
    
    def first_without_event(self, board_type, event_type):
        # assumes all serial numbers are four digit integers
        first = 1

        d = self._boarddir(board_type)
        for child in d.iterdir():
            sn = int(child.name)
            if self.has_event(f"{board_type}-{child.name}", event_type):
                if sn >= first:
                    first = sn + 1
        
        return "%s-%04d" % (board_type, first,)
