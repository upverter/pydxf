from __future__ import absolute_import
from builtins import object
import collections
from . import pydxf
from . import tools



class DxfTable(object):

    table_factories = None

    def __init__(self):
        self.name = ''
        self._records = []

    def add_records(self, record):
        tools.list_extend(self._records, record)

    @property
    def records(self):
        return self._records

    @staticmethod
    def __make_default_table(records):
        table = DxfTable()
        table.name = records[1].value
        table.add_records(records[1:-1])

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


class LayerTable(DxfTable):

    TABLE_TYPE = 'LAYER'

    def __init__(self):
        super(LayerTable, self).__init__()
        self.name = LayerTable.TABLE_TYPE
        self._layers = []

    def add_layers(self, layer):
        tools.list_extend(self._layers, layer)

    @property
    def layers(self):
        return self._layers

    @staticmethod
    def make_table(records):
        table = LayerTable()

        block_iter = tools.record_block_iterator(records, pydxf.DxfRecord(0, 'LAYER'), pydxf.DxfRecord(0, None))
        for layer_records in block_iter:
            table.add_layers(DxfLayer.make_layer(layer_records))

        table.add_records(block_iter.get_top_level_records())

        return table


class DxfLayer(object):

    def __init__(self):
        self.name = ''
        self.color_index = None

    @staticmethod
    def make_layer(records):
        ''' Construct a DxfLayer from a list of records.
        '''
        layer = DxfLayer()

        for record in records:
            if record.code == 2:
                layer.name = record.value
            elif record.code == 62:
                layer.color_index = int(record.value)

        return layer

    @staticmethod
    def make_default_layer(name):
        layer = DxfLayer()
        layer.name = name
        layer.color_index = 0
        return layer
