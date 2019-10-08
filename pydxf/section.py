from __future__ import absolute_import
from builtins import object
import collections
import copy
from . import pydxf
from . import entity, table, tools



class DxfSection(object):

    section_factories = None

    def __init__(self):
        self.name = ''
        self._records = []

    def add_records(self, record):
        tools.list_extend(self._records, record)

    @property
    def records(self):
        return self._records

    @staticmethod
    def __make_default_section(records):
        # Don't worry about checking data integrity - should already be done.
        section = DxfSection()
        section.name = records[1].value
        section.add_records(records[2:-1])

        return section

    @staticmethod
    def make_section(records):
        ''' Construct a DxfSection from a list of pydxf.DxfRecords.
        '''

        if len(records) < 3:
            raise pydxf.FormatException('Sections must consist of at least a start record, name record, and end record')
        if records[1].code != 2:
            raise pydxf.FormatException('Section records must be immediately followed by a section name record.')
        if not records[-1].is_section_end():
            raise pydxf.FormatException('Section records must end with an end record.')

        if not DxfSection.section_factories:
            DxfSection.populate_factory_table()

        return DxfSection.section_factories[records[1].value](records)

    @staticmethod
    def populate_factory_table():
        DxfSection.section_factories = collections.defaultdict(lambda: DxfSection.__make_default_section)
        for cls in DxfSection.__subclasses__():
            DxfSection.section_factories[cls.SECTION_TYPE] = cls.make_section


class EntitiesSection(DxfSection):

    SECTION_TYPE = 'ENTITIES'

    def __init__(self):
        super(EntitiesSection, self).__init__()
        self.name = EntitiesSection.SECTION_TYPE
        self.entities = []

    def add_entities(self, entity):
        tools.list_extend(self.entities, entity)

    def __len__(self):
        return len(self.entities)

    def __getitem__(self, key):
        return self.entities[key]

    def __iter__(self):
        return self.entities.__iter__()

    @staticmethod
    def make_section(records):
        section = EntitiesSection()

        block_iter = tools.record_block_iterator(records[2:], pydxf.DxfRecord(0, None), pydxf.DxfRecord(0, None))
        for entity_records in block_iter:
            section.add_entities(entity.DxfEntity.make_entity(entity_records))

        section.add_records(block_iter.get_top_level_records())

        return section


class HeaderSection(DxfSection):

    SECTION_TYPE = 'HEADER'

    def __init__(self):
        super(HeaderSection, self).__init__()
        self.name = HeaderSection.SECTION_TYPE
        self.variables = collections.defaultdict(lambda: None)

    def __len__(self):
        return len(self.variables)

    def __getitem__(self, key):
        return self.variables[key]

    def __iter__(self):
        return self.variables.__iter__()

    def iterkeys(self):
        return self.__iter__()

    def itervalues(self):
        return iter(self.variables.values())

    def iteritems(self):
        return iter(self.variables.items())

    def __contains__(self, key):
        return key in self.variables

    @staticmethod
    def make_section(records):
        section = HeaderSection()

        block_iter = tools.record_block_iterator(
            records, pydxf.DxfRecord(9, None), [pydxf.DxfRecord(9, None), pydxf.DxfRecord(0, 'ENDSEC')])

        for variable_records in block_iter:
            section._add_variable(*HeaderSection._make_variable(variable_records))

        section.add_records(block_iter.get_top_level_records())

        return section

    def _add_variable(self, name, value):
        self.variables[name] = value

    @staticmethod
    def _make_variable(records):
        # Not doing data validation. Caller should make sure data is valid.
        var_name = records[0].value.lstrip('$')
        var_val = records[1].value if len(records) == 2 else copy.deepcopy(records[1:])
        return var_name, var_val


class TablesSection(DxfSection):

    SECTION_TYPE = 'TABLES'

    def __init__(self):
        super(TablesSection, self).__init__()
        self.name = TablesSection.SECTION_TYPE
        self.tables = collections.defaultdict(lambda: None)

    def __len__(self):
        return len(self.tables)

    def __getitem__(self, key):
        return self.tables[key]

    def __iter__(self):
        return self.tables.__iter__()

    def iterkeys(self):
        return self.__iter__()

    def itervalues(self):
        return iter(self.tables.values())

    def iteritems(self):
        return iter(self.tables.items())

    def __contains__(self, key):
        return key in self.tables

    def add_table(self, table):
        self.tables[table.name] = table

    @staticmethod
    def make_section(records):
        section = TablesSection()

        block_iter = tools.record_block_iterator(
            records, pydxf.DxfRecord(0, 'TABLE'), pydxf.DxfRecord(0, 'ENDTAB'), True)

        for table_records in block_iter:
            section.add_table(table.DxfTable.make_table(table_records))

        section.add_records(block_iter.get_top_level_records())

        return section
