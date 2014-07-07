import itertools
import pydxf
import pydxf.tools
import StringIO
import unittest

class DxfParseTests(unittest.TestCase):

    SIMPLE = '''0
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
        itr = pydxf.tools.ascii_record_iterator(StringIO.StringIO(DxfParseTests.SIMPLE))
        rec1 = itr.next()
        assert rec1.code == 0 and rec1.value == 'SECTION'
        rec2 = itr.next()
        assert rec2.code == 2 and rec2.value == 'ENTITIES'
        rec3 = itr.next()
        assert rec3.code == 0 and rec3.value == 'ENDSEC'
        rec4 = itr.next()
        assert rec4.code == 0 and rec4.value == 'EOF'
        self.assertRaises(StopIteration, itr.next)

    def test_block_iterator_entities(self):
        dxf = '''0
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
        records = itertools.islice(pydxf.tools.ascii_record_iterator(StringIO.StringIO(dxf)), 2, None)
        block_iter = pydxf.tools.record_block_iterator(records, pydxf.DxfRecord(0, None), pydxf.DxfRecord(0, None))
        b1 = block_iter.next()
        assert len(b1) == 3
        assert b1[0].matches(pydxf.DxfRecord(0, 'LINE'))
        assert b1[1].matches(pydxf.DxfRecord(8, '0'))
        assert b1[2].matches(pydxf.DxfRecord(10, '0'))
        b2 = block_iter.next()
        assert len(b2) == 3
        assert b2[0].matches(pydxf.DxfRecord(0, 'LINE'))
        assert b2[1].matches(pydxf.DxfRecord(8, '0'))
        assert b2[2].matches(pydxf.DxfRecord(10, '1'))
        self.assertRaises(StopIteration, block_iter.next)

    def test_block_iterator_sections(self):
        dxf = '''0
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
        ENDSEC
        0
        EOF'''
        records = pydxf.tools.ascii_record_iterator(StringIO.StringIO(dxf))
        block_iter = pydxf.tools.record_block_iterator(records, pydxf.DxfRecord(0, 'SECTION'), pydxf.DxfRecord(0, 'ENDSEC'), True)
        b1 = block_iter.next()
        assert len(b1) == 3
        assert b1[0].matches(pydxf.DxfRecord(0, 'SECTION'))
        assert b1[1].matches(pydxf.DxfRecord(2, 'ENTITIES'))
        assert b1[2].matches(pydxf.DxfRecord(0, 'ENDSEC'))
        b2 = block_iter.next()
        assert len(b2) == 3
        assert b2[0].matches(pydxf.DxfRecord(0, 'SECTION'))
        assert b2[1].matches(pydxf.DxfRecord(2, 'TABLES'))
        assert b2[2].matches(pydxf.DxfRecord(0, 'ENDSEC'))
        self.assertRaises(StopIteration, block_iter.next)

    def test_block_iterator_multi_end(self):
        dxf = '''0
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
        records = pydxf.tools.ascii_record_iterator(StringIO.StringIO(dxf))
        block_iter = pydxf.tools.record_block_iterator(records, pydxf.DxfRecord(0, 'SECTION'), [pydxf.DxfRecord(0, 'ENDSEC'), pydxf.DxfRecord(0, 'EOF')], True)
        b1 = block_iter.next()
        assert len(b1) == 3
        assert b1[0].matches(pydxf.DxfRecord(0, 'SECTION'))
        assert b1[1].matches(pydxf.DxfRecord(2, 'ENTITIES'))
        assert b1[2].matches(pydxf.DxfRecord(0, 'ENDSEC'))
        b2 = block_iter.next()
        assert len(b2) == 3
        assert b2[0].matches(pydxf.DxfRecord(0, 'SECTION'))
        assert b2[1].matches(pydxf.DxfRecord(2, 'TABLES'))
        assert b2[2].matches(pydxf.DxfRecord(0, 'EOF'))
        self.assertRaises(StopIteration, block_iter.next)

    def test_unblocked_record_iterator(self):
        dxf = '''999
        Comment 1
        0
        SECTION
        2
        ENTITIES
        0
        ENDSEC
        999
        Comment 2
        0
        SECTION
        2
        TABLES
        0
        ENDSEC
        999
        Comment 3
        0
        EOF'''
        records = pydxf.tools.ascii_record_iterator(StringIO.StringIO(dxf))
        record_iter = pydxf.tools.unblocked_record_iterator(records, pydxf.DxfRecord(0, 'SECTION'), [pydxf.DxfRecord(0, 'ENDSEC'), pydxf.DxfRecord(0, 'EOF')], True)
        r1 = record_iter.next()
        assert r1.matches(pydxf.DxfRecord(999, 'Comment 1'))
        r2 = record_iter.next()
        assert r2.matches(pydxf.DxfRecord(999, 'Comment 2'))
        r3 = record_iter.next()
        assert r3.matches(pydxf.DxfRecord(999, 'Comment 3'))
        r4 = record_iter.next()
        assert r4.matches(pydxf.DxfRecord(0, 'EOF'))
        self.assertRaises(StopIteration, record_iter.next)

    def test_parse_simple_file(self):
        df = pydxf.DxfFile.make_file(pydxf.tools.ascii_record_iterator(StringIO.StringIO(DxfParseTests.SIMPLE)))
        assert len(list(df.iter_sections())) == 1
        sec = df.get_section('ENTITIES')
        assert len(list(sec.iter_records())) == 0

    def test_parse_truncated_file(self):
        # These kinds of truncated files appear to be generated by some versions of LibreCad
        dxf = StringIO.StringIO('''0
        SECTION
        2
        ENTITIES
        ''')

        df = pydxf.DxfFile.make_file(pydxf.tools.ascii_record_iterator(dxf))
        assert len(list(df.iter_sections())) == 1
        sec = df.get_section('ENTITIES')
        assert len(list(sec.iter_records())) == 0

if __name__ == '__main__':
    unittest.main()