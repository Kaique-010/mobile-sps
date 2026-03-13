import re


class LooseVersion:
    component_re = re.compile(r"(\\d+|[a-z]+|\\.)", re.I)

    def __init__(self, vstring=None):
        self.vstring = ""
        self.version = []
        if vstring is not None:
            self.parse(vstring)

    def __repr__(self):
        return f"{self.__class__.__name__} ({self.vstring!r})"

    def __str__(self):
        return self.vstring

    def parse(self, vstring):
        self.vstring = vstring
        components = [x for x in self.component_re.split(vstring) if x and x != "."]
        parsed = []
        for obj in components:
            try:
                parsed.append(int(obj))
            except ValueError:
                parsed.append(obj.lower())
        self.version = parsed

    def _cmp(self, other):
        if isinstance(other, str):
            other = LooseVersion(other)
        if not isinstance(other, LooseVersion):
            return NotImplemented
        if self.version == other.version:
            return 0
        if self.version < other.version:
            return -1
        return 1

    def __eq__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return False
        return c == 0

    def __lt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return False
        return c < 0

    def __le__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return False
        return c <= 0

    def __gt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return False
        return c > 0

    def __ge__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return False
        return c >= 0

    def __ne__(self, other):
        return not self.__eq__(other)

