import pydxf
import tools


def open_path(file_path):
    with open(file_path, 'rt') as fi:
        return pydxf.DxfFile.make_file(tools.ascii_record_iterator(fi))
