import collections
from . import entity, section, table, tools



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
            raise FormatException('Read group number <%s> is not a number.' % group)

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
        self._sections = {}

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
                    new_section = section.DxfSection.make_section(section_records)
                    dxf_file._sections[new_section.name] = new_section
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
            new_section = section.DxfSection.make_section(section_records)
            dxf_file._sections[new_section.name] = new_section

        return dxf_file

    @property
    def sections(self):
        return self._sections

    @property
    def layers(self):
        all_layers = tools.keyfaultdict(table.DxfLayer.make_default_layer)

        table_sec = self.sections.get('TABLES')
        if table_sec:
            layer_tab = table_sec.tables.get('LAYER')
            if layer_tab:
                for layer in layer_tab.layers:
                    all_layers[layer.name] = layer

        # Explicitly create default layers from the ENTITIES section so that (x in layers) works as expected
        entities_sec = self.sections.get('ENTITIES')
        if entities_sec:
            for entity in entities_sec.entities:
                if entity.layer_name not in all_layers:
                    all_layers[entity.layer_name] = table.DxfLayer.make_default_layer(entity.layer_name)

        return all_layers
