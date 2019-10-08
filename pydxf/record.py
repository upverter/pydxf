from builtins import object
from . import errors

class DxfRecord(object):
    # Record values of None are a special case created for defining 'rules' for the block iterator function. They
    # have no real meaning when it comes to DXF files. Might be helpful to break rules into a different class.

    def __init__(self, code, value):
        self.code = int(code)
        self.value = value

    @staticmethod
    def parse_from_stream(stream):
        group = stream.readline().strip()
        value = stream.readline().strip()

        if group == '':
            return None

        try:
            record = DxfRecord(group, value)
        except ValueError:
            raise errors.FormatException('Read group number <%s> is not a number.' % group)

        return record

    def is_section_end(self):
        return self.code == 0 and self.value == 'ENDSEC'

    def matches(self, record):
        if self.code != record.code:
            return False
        if self.value is None or record.value is None:
            return True
        return self.value == record.value

    def __repr__(self):
        return 'DxfRecord<%s, %s>' % (self.code, self.value)
