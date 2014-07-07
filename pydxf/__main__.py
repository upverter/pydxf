import pydxf
import sys
import Tkinter as tk
import tools



if __name__ == '__main__':
    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 400
    m = tk.Tk()
    window = tk.Canvas(m, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
    window.pack()
    window.create_rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, fill="white")

    fi = open(sys.argv[1], 'rt')
    df = pydxf.DxfFile.make_file(tools.ascii_record_iterator(fi))
    # print 'Version: %s' % df.get_section('HEADER').get_variable('ACADVER')

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

    # layer_table = df.get_section('TABLES').get_table('LAYER')
    # for layer in layer_table.iter_layers():
    #     print '%s %s' % (layer.name, layer.color_index)

    # window.create_line(40, 40, 40, 360)
    # window.create_line(40, 360, 360, 40, fill="green")
    # window.create_line(40, 360, 360, 360)
    # drawing.draw(window)
    tk.mainloop()


