import collections
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
    ''' Given a iterable collection of records, group the collection into lists of records using the block_start and
        block_end rules to determine block boundaries.
        block_end may be an iterable collection of rules, such that if any are encountered, the block ends.
    '''
    end_rules = _make_end_rules(block_end)

    in_block = False
    record_set = []

    for rec in records:
        if in_block:
            if any((rule.matches(rec) for rule in end_rules)):
                if include_end:
                    record_set.append(rec)
                    in_block = False
                    yield record_set
                    record_set = []
                else:
                    yield record_set
                    record_set = [rec]
            else:
                record_set.append(rec)
        else:
            if block_start.matches(rec):
                in_block = True
                record_set.append(rec)


def unblocked_record_iterator(records, block_start, block_end, include_end=False):
    ''' This is the compliment to the record_block_iterator - it returns records that are not part of a block.
    '''
    end_rules = _make_end_rules(block_end)

    in_block = False
    record_set = []

    for rec in records:
        if in_block:
            in_block = not any((rule.matches(rec) for rule in end_rules))
        else:
            in_block = block_start.matches(rec)
            if not in_block:
                yield rec
            elif in_block and not include_end:
                # We're done if we don't include end blocks, since there's no way to indicate the end of a block.
                break


def _make_end_rules(block_end):
    if isinstance(block_end, pydxf.DxfRecord):
        return [block_end]
    elif isinstance(block_end, collections.Iterable):
        return list(block_end)
    else:
        raise TypeError
