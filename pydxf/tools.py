import collections
import copy
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


def list_extend(list, items):
    ''' Helper function for appending things to a list. If items is some kind of iterable, then each element of items
        is appended to list. Otherwise, the value of items is appended.
    '''
    if isinstance(items, collections.Iterable):
        list.extend(items)
    else:
        list.append(items)


class record_block_iterator(object):
    ''' Given a iterable collection of records, group the collection into lists of records using the block_start and
        block_end rules to determine block boundaries. Once the generator has run through completely, any records from
        the supplied set that aren't a member of a block can be accessed from the get_top_level_records method.
        block_end may be an iterable collection of rules, such that if any are encountered, the block ends.
    '''

    def __init__(self, records, block_start, block_end, include_end=False):
        self.records = (rec for rec in records)
        self.block_start = block_start
        self.block_end = block_end
        self.include_end = include_end
        self.end_rules = record_block_iterator._make_end_rules(block_end)
        self.top_level_records = []
        self.in_block = False
        self.exhausted = False
        self.next_set = []

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def get_top_level_records(self):
        if self.exhausted:
            return self.top_level_records

        raise RuntimeError('get_top_level_records called on record_block_iterator before generator is exhausted.')

    @staticmethod
    def _make_end_rules(block_end):
        if isinstance(block_end, pydxf.DxfRecord):
            return [block_end]
        elif isinstance(block_end, collections.Iterable):
            return list(block_end)
        else:
            raise TypeError

    def next(self):
        record_set = copy.copy(self.next_set)
        self.next_set = []

        for rec in self.records:
            if self.in_block:
                if any(rule.matches(rec) for rule in self.end_rules):
                    if self.include_end:
                        record_set.append(rec)
                        self.in_block = False
                        break
                    else:
                        self.next_set.append(rec)
                        break
                else:
                    record_set.append(rec)
            else:
                if self.block_start.matches(rec):
                    self.in_block = True
                    record_set.append(rec)
                else:
                    self.top_level_records.append(rec)
        else:
            self.exhausted = True
            raise StopIteration

        return record_set
