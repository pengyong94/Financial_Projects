from dataclasses import dataclass, asdict, field
from typing import Dict, List

# Response
@dataclass
class BaseResponse:
    code: int = 200
    msg: str = 'success'
    error_info: str = ''

    def __update__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return asdict(self)

@dataclass
class ServerResponse(BaseResponse):
    role: str = 'client'
    trace_id: str = 'x1234567890x'
    result: Dict = field(default_factory=dict)


# Exceptions
class TimeoutException(Exception):
    code: int = 700
    error_info: str = 'Timeout'

class InputException(Exception):
    code: int = 415

class KBNotFoundException(Exception):
    code: int = 404

    def __init__(self, kb_id):
        self.error_info = f'Knowledge Base ```{kb_id}``` is not available'

class ProcessException(Exception):
    def __init__(self, response, error_info):
        self.code = response.code
        self.error_info = error_info

class OtherException(Exception):
    code: int = 600
