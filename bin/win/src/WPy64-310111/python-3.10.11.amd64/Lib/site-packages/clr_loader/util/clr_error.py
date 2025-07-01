from typing import Optional


class ClrError(Exception):
    def __init__(
        self,
        hresult: int,
        name: Optional[str] = None,
        message: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        self.hresult = hresult
        self.name = name
        self.message = message
        self.comment = comment
        super().__init__(self.message)

    def __str__(self):
        if self.message:
            return f"{hex(self.hresult)}: {self.name} => {self.message}"
        elif self.name:
            return f"{hex(self.hresult)}: {self.name}"
        else:
            return f"{hex(self.hresult)}"

    def __repr__(self):
        return f"<ClrError {str(self)}>"
