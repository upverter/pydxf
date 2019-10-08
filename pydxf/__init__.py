from __future__ import absolute_import
import io
from . import pydxf
from . import tools


def open_path(file_path):
    with open(file_path, 'rt') as fi:
        if not tools.is_ascii_dxf(fi):
            raise pydxf.FormatException('File does not appear to be ASCII DXF')

        fi.seek(0, io.SEEK_SET)
        return pydxf.DxfFile.make_file(tools.ascii_record_iterator(fi))
