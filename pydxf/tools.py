import pydxf



def ascii_record_iterator(stream):
    ''' Return a sequence of DxfRecords as parsed from a stream representing an ASCII DXF file.
        stream - Any stream supporting the readline method. Stream does not need to be seekable.
    '''

    while True:
        rec = pydxf.DxfRecord.parse_from_stream(stream)
        if rec is None:
            break
        yield rec


def record_block_iterator(records, block_start, block_end, include_end=False):
    ''' Given a list of records, group the list into sub-lists based on the block_start and block_end records, and
        iterate over those blocks of records.
    '''

    in_block = False
    start_index = 0

    for i, rec in enumerate(records):
        if in_block:
            if block_end.matches(rec):
                if include_end:
                    yield records[start_index:i+1]
                    in_block = False
                else:
                    yield records[start_index:i]
                    start_index = i
        else:
            if block_start.matches(rec):
                in_block = True
                start_index = i
