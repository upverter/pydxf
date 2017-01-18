import collections
import pydxf
from . import tools



class DxfEntity(object):

    entity_factories = None

    def __init__(self):
        self.name = ''
        self._records = []
        self.layer_name = ''

    def add_records(self, record):
        tools.list_extend(self._records, record)

    @property
    def records(self):
        return self._records

    @staticmethod
    def __make_default_entity(records):
        # Don't worry about error checking. Should be done already.
        entity = DxfEntity()
        entity.name = records[0].value

        for rec in records[1:]:
            if rec.code == 8:
                entity.layer_name = rec.value
            else:
                entity.add_records(rec)

        return entity

    @staticmethod
    def make_entity(records):
        ''' Construct a DxfEntity from a list of records.
        '''

        if len(records) <= 0:
            raise pydxf.FormatException('Entities must have at least one record.')

        if not DxfEntity.entity_factories:
            DxfEntity.populate_factory_table()

        return DxfEntity.entity_factories[records[0].value](records)

    @staticmethod
    def populate_factory_table():
        DxfEntity.entity_factories = collections.defaultdict(lambda: DxfEntity.__make_default_entity)
        for cls in DxfEntity.__subclasses__():
            DxfEntity.entity_factories[cls.ENTITY_TYPE] = cls.make_entity


class ArcEntity(DxfEntity):

    ENTITY_TYPE = 'ARC'

    def __init__(self):
        super(ArcEntity, self).__init__()
        self.name = ArcEntity.ENTITY_TYPE
        self.x = 0
        self.y = 0
        self.radius = 0
        self.start_angle = 0
        self.end_angle = 0
        self.layer_name = ''
        self.z_dir = 1

    @staticmethod
    def make_entity(records):
        entity = ArcEntity()

        for rec in records:
            if rec.code == 8:
                entity.layer_name = rec.value
            elif rec.code == 10:
                entity.x = float(rec.value)
            elif rec.code == 20:
                entity.y = float(rec.value)
            elif rec.code == 40:
                entity.radius = float(rec.value)
            elif rec.code == 50:
                entity.start_angle = float(rec.value)
            elif rec.code == 51:
                entity.end_angle = float(rec.value)
            elif rec.code == 230:
                entity.z_dir = float(rec.value)
            else:
                entity.add_records(rec)

        return entity


class CircleEntity(DxfEntity):

    ENTITY_TYPE = 'CIRCLE'

    def __init__(self):
        super(CircleEntity, self).__init__()
        self.name = CircleEntity.ENTITY_TYPE
        self.x = 0
        self.y = 0
        self.radius = 0
        self.layer_name = ''
        self.z_dir = 1

    @staticmethod
    def make_entity(records):
        entity = CircleEntity()

        for rec in records:
            if rec.code == 8:
                entity.layer_name = rec.value
            elif rec.code == 10:
                entity.x = float(rec.value)
            elif rec.code == 20:
                entity.y = float(rec.value)
            elif rec.code == 40:
                entity.radius = float(rec.value)
            elif rec.code == 230:
                entity.z_dir = float(rec.value)
            else:
                entity.add_records(rec)

        return entity


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
        self.z_dir = 1

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
            elif rec.code == 230:
                entity.z_dir = float(rec.value)
            else:
                entity.add_records(rec)

        return entity


class PolyLineEntity(DxfEntity):

    ENTITY_TYPE = 'POLYLINE'

    def __init__(self):
        super(PolyLineEntity, self).__init__()
        self.name = PolyLineEntity.ENTITY_TYPE
        self.layer_name = ''

    @staticmethod
    def make_entity(records):
        entity = PolyLineEntity()

        for rec in records:
            if rec.code == 8:
                entity.layer_name = rec.value
            else:
                entity.add_records(rec)

        return entity


class VertexEntity(DxfEntity):

    ENTITY_TYPE = 'VERTEX'

    def __init__(self):
        super(VertexEntity, self).__init__()
        self.name = VertexEntity.ENTITY_TYPE
        self.layer_name = ''
        self.x = 0
        self.y = 0
        self.z = 0
        self.bulge = 0

    @staticmethod
    def make_entity(records):
        entity = VertexEntity()

        for rec in records:
            if rec.code == 8:
                entity.layer_name = rec.value
            elif rec.code == 10:
                entity.x = float(rec.value)
            elif rec.code == 20:
                entity.y = float(rec.value)
            elif rec.code == 30:
                entity.z = float(rec.value)
            elif rec.code == 42:
                entity.bulge = float(rec.value)
            else:
                entity.add_records(rec)

        return entity


class SeqEndEntity(DxfEntity):

    ENTITY_TYPE = 'SEQEND'

    def __init__(self):
        super(SeqEndEntity, self).__init__()
        self.name = SeqEndEntity.ENTITY_TYPE
        self.layer_name = ''

    @staticmethod
    def make_entity(records):
        entity = SeqEndEntity()

        for rec in records:
            entity.add_records(rec)

        return entity
