import collections
import copy
import Tkinter as tk



class FormatException(Exception):
    pass


class UnknownEntityException(Exception):
    pass


class UnexpectedEOFException(Exception):
    pass


class DxfRecord(object):

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
            raise FormatException('Read group number <%s> is not a number.', group)

        return record

    def is_section_end(self):
        return self.code == 0 and self.value == 'ENDSEC'

    def __repr__(self):
        return 'DxfRecord<%s, %s>' % (self.code, self.value)


class DxfEntity(object):

    entity_factories = None

    def __init__(self):
        self.name = ''
        self.records = []

    def add_record(self, record):
        self.records.append(record)

    def iter_records(self):
        for rec in self.records:
            yield rec

    @staticmethod
    def __make_default_entity(records):
        # Don't worry about error checking. Should be done already.
        entity = DxfEntity()
        entity.name = records[0].value

        for rec in records[1:]:
            entity.add_record(rec)

        return entity

    @staticmethod
    def make_entity(records):
        ''' Construct a DxfEntity from a list of records.
        '''

        if len(records) <= 0:
            raise FormatException('Entities must have at least one record.')

        if not DxfEntity.entity_factories:
            DxfEntity.populate_factory_table()

        return DxfEntity.entity_factories[records[0].value](records)

    @staticmethod
    def populate_factory_table():
        DxfEntity.entity_factories = collections.defaultdict(lambda: DxfEntity.__make_default_entity)
        for cls in DxfEntity.__subclasses__():
            DxfEntity.entity_factories[cls.ENTITY_TYPE] = cls.make_entity


class DxfTable(object):

    table_factories = None

    def __init__(self):
        self.name = ''
        self.records = []

    def add_record(self, record):
        self.records.append(record)

    def iter_records(self):
        for rec in self.records:
            yield rec

    @staticmethod
    def __make_default_table(records):
        table = DxfTable()
        table.name = records[1].value

        for rec in records[1:-1]:
            table.add_record(rec)

        return table

    @staticmethod
    def make_table(records):
        ''' Construct a DxfTable from a list of records.
        '''

        if len(records) < 3:
            raise FormatException('Tables must have at least a start record, name record, and end record')
        if records[1].code != 2:
            raise FormatException('The second record in a table definition must be the table name')
        if records[-1].code != 0 or records[-1].value != 'ENDTAB':
            raise FormatException('The last record in a table definition must be an end record')

        if not DxfTable.table_factories:
            DxfTable.populate_factory_table()

        return DxfTable.table_factories[records[1].value](records)

    @staticmethod
    def populate_factory_table():
        DxfTable.table_factories = collections.defaultdict(lambda: DxfTable.__make_default_table)
        for cls in DxfTable.__subclasses__():
            DxfTable.table_factories[cls.TABLE_TYPE] = cls.make_table


class LineEntity(DxfEntity):

    ENTITY_TYPE = 'LINE'

    def __init__(self):
        super(LineEntity, self).__init__()
        self.name = LineEntity.ENTITY_TYPE
        self.layer_name = ''
        self.x1 = 0
        self.x2 = 0
        self.y1 = 0
        self.y2 = 0

    @staticmethod
    def make_entity(records):
        entity = LineEntity()

        for rec in records:
            if rec.code == 8:
                entity.layer_name = rec.value
            elif rec.code == 10:
                entity.x1 = float(rec.value)
            elif rec.code == 11:
                entity.x2 = float(rec.value)
            elif rec.code == 20:
                entity.y1 = float(rec.value)
            elif rec.code == 21:
                entity.y2 = float(rec.value)
            else:
                entity.add_record(rec)

        return entity


class DxfSection(object):

    section_factories = None

    def __init__(self):
        self.name = ''
        self.records = []

    def add_record(self, record):
        self.records.append(record)

    def iter_records(self):
        for rec in self.records:
            yield rec

    @staticmethod
    def __make_default_section(records):
        # Don't worry about checking data integrity - should already be done.
        section = DxfSection()
        section.name = records[1].value

        for record in records[2:-1]:
            section.add_record(record)

        return section

    @staticmethod
    def make_section(records):
        ''' Construct a DxfSection from a list of DxfRecords.
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

    def add_entity(self, entity):
        self.entities.append(entity)

    def iter_entities(self):
        for entity in self.entities:
            yield entity

    @staticmethod
    def make_section(records):
        section = EntitiesSection()
        building_entity_records = False
        start_index = 0

        for i, rec in enumerate(records[2:], 2):
            if building_entity_records:
                if rec.code == 0:
                    # Start of next entity or ENDSEC record has been reached.
                    section.add_entity(DxfEntity.make_entity(records[start_index:i]))
                    start_index = i
            else:
                if rec.code == 0:
                    building_entity_records = True
                    start_index = i
                else:
                    section.add_record(rec)

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
        building_variable = False
        start_index = 0

        for i, rec in enumerate(records[2:], 2):
            if building_variable:
                if rec.is_section_end() or rec.code == 9:
                    section._add_variable(*HeaderSection._make_variable(records[start_index:i]))
                    start_index = i
            else:
                if rec.code == 9:
                    start_index = i
                    building_variable = True
                else:
                    section.add_record(rec)

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
        building_table = False
        start_index = 0

        for i, rec in enumerate(records[2:-1], 2):
            if building_table:
                if rec.code == 0 and rec.value == 'ENDTAB':
                    section.add_table(DxfTable.make_table(records[start_index:i+1]))
                    building_table = False
            else:
                if rec.code == 0:
                    building_table = True
                    start_index = i
                else:
                    section.add_record(rec)

        return section


class DxfFile(object):

    section_factories = {}

    def __init__(self):
        self.sections = []

    @staticmethod
    def make_file(records):
        ''' Construct a DxfFile from an iterable of DxfRecords.
        '''

        dxf_file = DxfFile()

        # State machine with two states. Either putting together records to construct a section, or not.
        building_section_records = False
        section_records = []

        for rec in records:
            if building_section_records:
                section_records.append(rec)
                if rec.is_section_end():
                    building_section_records = False
                    dxf_file.sections.append(DxfSection.make_section(section_records))
            else:
                if rec.code == 0 and rec.value == 'SECTION':
                    building_section_records = True
                    section_records = []
                    section_records.append(rec)
                # if rec.code == 0 and rec.value == 'EOF':
                #    # Should be the last record in the file. Don't care.
                #    pass
                # if rec.code == 999:
                #    # This is a top-level comment. Ignore.
                #    pass
                # else:
                #    # Got some other top-level record. I think this indicates an error with the file.
                #    pass

        if building_section_records:
            # The file appears to have been truncated because we never got an ENDSEC for the last section we were
            # working on. LibreCAD seems to create files like this.
            section_records.append(DxfRecord(0, 'ENDSEC'))
            dxf_file.sections.append(DxfSection.make_section(section_records))

        return dxf_file

    @staticmethod
    def ascii_record_iterator(stream):
        ''' Return a sequence of DxfRecords as parsed from a stream representing an ASCII DXF file.
            stream - Any stream supporting the readline method. Stream does not need to be seekable.
        '''

        while True:
            rec = DxfRecord.parse_from_stream(stream)
            if rec is None:
                break
            yield rec

    def iter_sections(self):
        if not self.sections:
            self.parse_sections()

        for section in self.sections:
            yield section

    def get_section(self, name):
        if not self.sections:
            self.parse_sections()

        for section in self.sections:
            if section.name == name:
                return section

    def update_section(self, new_section):
        for i, section in enumerate(self.sections):
            if section.name == new_section.name:
                self.sections[i] = new_section
                break


if __name__ == '__main__':
    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 400
    m = tk.Tk()
    window = tk.Canvas(m, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
    window.pack()
    window.create_rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, fill="white")

    fi = open('drawing1.dxf', 'rt')
    df = DxfFile.make_file(DxfFile.ascii_record_iterator(fi))
    print 'Version: %s' % df.get_section('HEADER').get_variable('ACADVER')

    # df = DxfFile(fi)
    for section in df.iter_sections():
        # print section.name
        for rec in section.iter_records():
            pass
            # print '\t%s %s' % (rec.code, rec.value)
        if section.name == 'ENTITIES':
            for entity in section.iter_entities():
                # print entity.name
                if entity.name == 'LINE':
                    # window.create_line(25+entity.x1*40, WINDOW_HEIGHT-(25+entity.y1*40), 25+entity.x2*40, WINDOW_HEIGHT-(25+entity.y2*40))
                    window.create_line(25+entity.x1, WINDOW_HEIGHT-(25+entity.y1), 25+entity.x2, WINDOW_HEIGHT-(25+entity.y2))
                    # print '\tLINE %s,%s to %s,%s' % (entity.x1, entity.y1, entity.x2, entity.y2)

    for table in df.get_section('TABLES').iter_tables():
        print table.name

    # window.create_line(40, 40, 40, 360)
    # window.create_line(40, 360, 360, 40, fill="green")
    # window.create_line(40, 360, 360, 360)
    # drawing.draw(window)
    tk.mainloop()


