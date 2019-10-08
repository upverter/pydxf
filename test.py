from future import standard_library
standard_library.install_aliases()
import decimal
import itertools
import pydxf
from pydxf.record import DxfRecord
import pydxf.tools
import io
import unittest

class DxfParseTests(unittest.TestCase):

    SIMPLE = u'''0
    SECTION
    2
    ENTITIES
    0
    ENDSEC
    0
    EOF'''

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ascii_record_iterator(self):
        itr = pydxf.tools.ascii_record_iterator(io.StringIO(DxfParseTests.SIMPLE))
        rec1 = next(itr)
        assert rec1.code == 0 and rec1.value == 'SECTION'
        rec2 = next(itr)
        assert rec2.code == 2 and rec2.value == 'ENTITIES'
        rec3 = next(itr)
        assert rec3.code == 0 and rec3.value == 'ENDSEC'
        rec4 = next(itr)
        assert rec4.code == 0 and rec4.value == 'EOF'
        self.assertRaises(StopIteration, lambda: next(itr))

    def test_block_iterator_entities(self):
        dxf = u'''0
        SECTION
        2
        ENTITIES
        999
        This is a comment
        0
        LINE
        8
        0
        10
        0
        0
        LINE
        8
        0
        10
        1
        0
        ENDSEC'''
        records = itertools.islice(pydxf.tools.ascii_record_iterator(io.StringIO(dxf)), 2, None)
        block_iter = pydxf.tools.record_block_iterator(records, DxfRecord(0, None), DxfRecord(0, None))
        b1 = next(block_iter)
        assert len(b1) == 3
        assert b1[0].matches(DxfRecord(0, 'LINE'))
        assert b1[1].matches(DxfRecord(8, '0'))
        assert b1[2].matches(DxfRecord(10, '0'))
        b2 = next(block_iter)
        assert len(b2) == 3
        assert b2[0].matches(DxfRecord(0, 'LINE'))
        assert b2[1].matches(DxfRecord(8, '0'))
        assert b2[2].matches(DxfRecord(10, '1'))
        self.assertRaises(StopIteration, block_iter.__next__)

        top_level = block_iter.get_top_level_records()
        assert len(top_level) == 1
        assert top_level[0].matches(DxfRecord(999, 'This is a comment'))

    def test_block_iterator_sections(self):
        dxf = u'''0
        SECTION
        2
        ENTITIES
        0
        ENDSEC
        999
        This is a comment
        0
        SECTION
        2
        TABLES
        0
        ENDSEC
        0
        EOF'''
        records = pydxf.tools.ascii_record_iterator(io.StringIO(dxf))
        block_iter = pydxf.tools.record_block_iterator(records, DxfRecord(0, 'SECTION'), DxfRecord(0, 'ENDSEC'), True)
        b1 = next(block_iter)
        assert len(b1) == 3
        assert b1[0].matches(DxfRecord(0, 'SECTION'))
        assert b1[1].matches(DxfRecord(2, 'ENTITIES'))
        assert b1[2].matches(DxfRecord(0, 'ENDSEC'))
        b2 = next(block_iter)
        assert len(b2) == 3
        assert b2[0].matches(DxfRecord(0, 'SECTION'))
        assert b2[1].matches(DxfRecord(2, 'TABLES'))
        assert b2[2].matches(DxfRecord(0, 'ENDSEC'))
        self.assertRaises(StopIteration, block_iter.__next__)

        top_level = block_iter.get_top_level_records()
        assert len(top_level) == 2
        assert top_level[0].matches(DxfRecord(999, 'This is a comment'))
        assert top_level[1].matches(DxfRecord(0, 'EOF'))

    def test_block_iterator_multi_end(self):
        dxf = u'''0
        SECTION
        2
        ENTITIES
        0
        ENDSEC
        0
        SECTION
        2
        TABLES
        0
        EOF
        999
        This is a comment
        0
        ENDSEC'''
        records = pydxf.tools.ascii_record_iterator(io.StringIO(dxf))
        block_iter = pydxf.tools.record_block_iterator(records, DxfRecord(0, 'SECTION'), [DxfRecord(0, 'ENDSEC'), DxfRecord(0, 'EOF')], True)
        b1 = next(block_iter)
        assert len(b1) == 3
        assert b1[0].matches(DxfRecord(0, 'SECTION'))
        assert b1[1].matches(DxfRecord(2, 'ENTITIES'))
        assert b1[2].matches(DxfRecord(0, 'ENDSEC'))
        b2 = next(block_iter)
        assert len(b2) == 3
        assert b2[0].matches(DxfRecord(0, 'SECTION'))
        assert b2[1].matches(DxfRecord(2, 'TABLES'))
        assert b2[2].matches(DxfRecord(0, 'EOF'))
        self.assertRaises(StopIteration, block_iter.__next__)

        top_level = block_iter.get_top_level_records()
        assert len(top_level) == 2
        assert top_level[0].matches(DxfRecord(999, 'This is a comment'))
        assert top_level[1].matches(DxfRecord(0, 'ENDSEC'))

    def test_parse_simple_file(self):
        df = pydxf.file.DxfFile.make_file(pydxf.tools.ascii_record_iterator(io.StringIO(DxfParseTests.SIMPLE)))
        assert len(list(df.sections)) == 1
        sec = df.sections['ENTITIES']
        assert len(list(sec.records)) == 0

    def test_parse_truncated_file(self):
        # These kinds of truncated files appear to be generated by some versions of LibreCad
        dxf = io.StringIO(u'''0
        SECTION
        2
        ENTITIES
        ''')

        df = pydxf.file.DxfFile.make_file(pydxf.tools.ascii_record_iterator(dxf))
        assert len(list(df.sections)) == 1
        sec = df.sections['ENTITIES']
        assert len(list(sec.records)) == 0

    def test_list_extend_single(self):
        base_list = [1, 2]
        pydxf.tools.list_extend(base_list, 3)
        assert len(base_list) == 3
        assert base_list[0] == 1
        assert base_list[1] == 2
        assert base_list[2] == 3

    def test_list_extend_multiple(self):
        base_list = [1, 2]
        pydxf.tools.list_extend(base_list, [3, 4])
        assert len(base_list) == 4
        assert base_list[0] == 1
        assert base_list[1] == 2
        assert base_list[2] == 3
        assert base_list[3] == 4

    def test_convert_to_meters(self):
        self.assertEqual(pydxf.tools.convert_to_meters(6, 'INCHES'), decimal.Decimal('0.1524'))
        self.assertEqual(pydxf.tools.convert_to_meters(50, 4), decimal.Decimal('0.05'))
        self.assertEqual(pydxf.tools.convert_to_meters(1000, 'MICRONS'), decimal.Decimal('0.001'))

    def test_convert_from_meters(self):
        self.assertEqual(pydxf.tools.convert_from_meters(decimal.Decimal('0.1524'), 'INCHES'), decimal.Decimal('6'))
        self.assertEqual(pydxf.tools.convert_from_meters(decimal.Decimal('0.05'), 4), decimal.Decimal('50'))
        self.assertEqual(pydxf.tools.convert_from_meters(decimal.Decimal('0.001'), 'MICRONS'), decimal.Decimal('1000'))

    def test_convert_units(self):
        self.assertEqual(pydxf.tools.convert_units(6, 'INCHES', 'NANOMETERS'), decimal.Decimal('152400000'))
        self.assertEqual(pydxf.tools.convert_units(50, 'MILLIMETERS', 'NANOMETERS'), decimal.Decimal('50000000'))

if __name__ == '__main__':
    unittest.main()
