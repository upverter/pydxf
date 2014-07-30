import collections
import copy
import pydxf
import entity, table, tools



class DxfSection(object):

    section_factories = None

    def __init__(self):
        self.name = ''
        self.records = []

    def add_records(self, record):
        tools.list_extend(self.records, record)

    def iter_records(self):
        for rec in self.records:
            yield rec

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
            raise FormatException('Sections must consist of at least a start record, name record, and end record')
        if records[1].code != 2:
            raise FormatException('Section records must be immediately followed by a section name record.')
        if not records[-1].is_section_end():
            raise FormatException('Section records must end with an end record.')

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

    def iter_entities(self):
        for entity in self.entities:
            yield entity

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

    def get_variable(self, name):
        return self.variables[name]

    @staticmethod
    def make_section(records):
        section = HeaderSection()

        block_iter = tools.record_block_iterator(records, pydxf.DxfRecord(9, None), [pydxf.DxfRecord(9, None), pydxf.DxfRecord(0, 'ENDSEC')])
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
        return var_name, records[1].value if len(records) == 2 else copy.deepcopy(records[1:])


class TablesSection(DxfSection):

    SECTION_TYPE = 'TABLES'

    def __init__(self):
        super(TablesSection, self).__init__()
        self.name = TablesSection.SECTION_TYPE
        self.tables = collections.defaultdict(lambda: None)

    def get_table(self, name):
        return self.tables[name]

    def add_table(self, table):
        self.tables[table.name] = table

    def iter_tables(self):
        for table in self.tables.values():
            yield table

    @staticmethod
    def make_section(records):
        section = TablesSection()

        block_iter = tools.record_block_iterator(records, pydxf.DxfRecord(0, 'TABLE'), pydxf.DxfRecord(0, 'ENDTAB'), True)
        for table_records in block_iter:
            section.add_table(table.DxfTable.make_table(table_records))

        section.add_records(block_iter.get_top_level_records())

        return section
