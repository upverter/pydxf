import pydxf
import sys
import Tkinter as tk
import tools



class DxfWindow(object):

    def __init__(self, file):
        self.width = 750
        self.height = 600
        self.SCALE = 1
        self.SHIFT_X = 0
        self.SHIFT_Y = 0
        self.file = file

        self.move_x = 0
        self.move_y = 0

        m = tk.Tk()
        self.window = tk.Canvas(m, width=self.width, height=self.height)
        self.window.pack()
        self.window.bind('<Button-1>', self.mouse_down)
        self.window.bind('<ButtonRelease-1>', self.mouse_up)
        self.window.bind('<Button-4>', self.wheel_up)
        self.window.bind('<Button-5>', self.wheel_down)

    def draw_dxf(self, tx, ty, zoom):
        self.window.create_rectangle(0, 0, self.width, self.height, fill='#dedede')

        for section in self.file.iter_sections():
            for rec in section.iter_records():
                pass
            if section.name == 'ENTITIES':
                for entity in section.iter_entities():
                    if entity.name == 'LINE':
                        x1 = entity.x1 * zoom + tx
                        x2 = entity.x2 * zoom + tx
                        y1 = entity.y1 * zoom + ty
                        y2 = entity.y2 * zoom + ty
                        color = tools.COLORS[df.get_layer(entity.layer_name).color_index]
                        self.window.create_line(x1, self.height - y1, x2, self.height - y2, fill=color)
                        # print '\tLINE %s,%s to %s,%s' % (entity.x1, entity.y1, entity.x2, entity.y2)
                    elif entity.name == 'CIRCLE':
                        x1 = (entity.x - entity.radius) * zoom + tx
                        x2 = (entity.x + entity.radius) * zoom + tx
                        y1 = (entity.y - entity.radius) * zoom + ty
                        y2 = (entity.y + entity.radius) * zoom + ty
                        color = tools.COLORS[df.get_layer(entity.layer_name).color_index]
                        self.window.create_oval(x1, self.height - y1, x2, self.height - y2, outline=color)
                    elif entity.name == 'ARC':
                        x1 = (entity.x - entity.radius) * zoom + tx
                        x2 = (entity.x + entity.radius) * zoom + tx
                        y1 = (entity.y - entity.radius) * zoom + ty
                        y2 = (entity.y + entity.radius) * zoom + ty
                        sa = entity.start_angle
                        if entity.start_angle > entity.end_angle:
                            ea = entity.end_angle + (360 - entity.start_angle)
                        else:
                            ea = entity.end_angle - entity.start_angle
                        color = tools.COLORS[df.get_layer(entity.layer_name).color_index]
                        self.window.create_arc(x1, self.height - y1, x2, self.height - y2, start=sa, extent=ea, style=tk.ARC, outline=color)

        self.window.create_text(self.width - 60, self.height - 15, text='Scale: %s' % self.SCALE)

    def mouse_down(self, event):
        # print 'Mouse'
        self.move_x = event.x
        self.move_y = event.y

    def mouse_up(self, event):
        delta_x = event.x - self.move_x
        delta_y = event.y - self.move_y
        self.SHIFT_X += delta_x
        self.SHIFT_Y -= delta_y
        self.redraw()

    def wheel_up(self, event):
        # print 'Wheel up'
        if self.SCALE >= 5:
            self.SCALE += 5
        else:
            self.SCALE += 1
        self.redraw()

    def wheel_down(self, event):
        # print 'Wheel down'
        if self.SCALE <= 5:
            self.SCALE -= 1
        else:
            self.SCALE -= 5
        self.redraw()

    def redraw(self):
        self.draw_dxf(self.SHIFT_X, self.SHIFT_Y, self.SCALE)


if __name__ == '__main__':


    fi = open(sys.argv[1], 'rt')
    df = pydxf.DxfFile.make_file(tools.ascii_record_iterator(fi))
    dw = DxfWindow(df)
    dw.redraw()

    # layer_table = df.get_section('TABLES').get_table('LAYER')
    # for layer in layer_table.iter_layers():
    #     print '%s %s' % (layer.name, layer.color_index)

    tk.mainloop()


