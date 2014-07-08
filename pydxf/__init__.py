import collections
import entity
import section
import table
import tools



class FormatException(Exception):
    pass


class UnknownEntityException(Exception):
    pass


class UnexpectedEOFException(Exception):
    pass


class DxfRecord(object):
    # Record values of None are a special case created for defining 'rules' for the block iterator function. They
    # have no real meaning when it comes to DXF files. Might be helpful to break rules into a different class.

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

    def matches(self, record):
        if self.code != record.code:
            return False
        if self.value is None or record.value is None:
            return True
        return self.value == record.value

    def __repr__(self):
        return 'DxfRecord<%s, %s>' % (self.code, self.value)


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
                    dxf_file.sections.append(section.DxfSection.make_section(section_records))
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
            dxf_file.sections.append(section.DxfSection.make_section(section_records))

        return dxf_file

    def iter_sections(self):
        for section in self.sections:
            yield section

    def get_section(self, name):
        for section in self.sections:
            if section.name == name:
                return section

    def update_section(self, new_section):
        for i, section in enumerate(self.sections):
            if section.name == new_section.name:
                self.sections[i] = new_section
                break

    def get_layer(self, layer_name):
        table_sec = self.get_section('TABLES')
        if not table_sec:
            return table.DxfLayer.make_default_layer(layer_name)

        layer_tab = table_sec.get_table('LAYER')
        if not layer_tab:
            return table.DxfLayer.make_default_layer(layer_name)

        for layer in layer_tab.iter_layers():
            if layer.name == layer_name:
                return layer

        return table.DxfLayer.make_default_layer(layer_name)
