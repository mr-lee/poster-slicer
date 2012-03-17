#!/usr/bin/python
import gtk
import gtk.gdk
import cairo
from sys import argv
from PIL import Image

class ImgDisplay(gtk.DrawingArea):

    def __init__(self, pic_name):
        gtk.DrawingArea.__init__(self)

        #some constants
        self.paper_ratio = 8.5/11 # letter sized paper ratio
        self.std_height = 500 # standard height to scale to
        
        #temporary, initial variables
        self.height = 4
        self.portrait = True

        #load in the picture and scale it
        imgbuf = gtk.gdk.pixbuf_new_from_file(pic_name)
        scale_r = float(self.std_height)/imgbuf.get_height()
        self.pixbuf = imgbuf.scale_simple(int(imgbuf.get_width()*scale_r), self.std_height, gtk.gdk.INTERP_HYPER)
        self.set_size_request(self.pixbuf.get_width(),self.pixbuf.get_height())

        self.pic_name = pic_name
        self.connect("expose_event", self.expose)

    def expose(self,widget,event):
        self.cairo_cxt = widget.window.cairo_create()
        self.cairo_cxt.set_line_width(1)
        self.cairo_cxt.set_dash([5,2.5])
        #create gdk context for widget.window
        gdk_cxt = widget.window.new_gc()
        color = gdk_cxt.get_colormap().alloc_color("white")
        gdk_cxt.set_foreground(color)
        #draw a white rectangle
        widget.window.draw_rectangle(gdk_cxt, filled=True, x = 0, y = 0, width = self.pixbuf.get_width(), 
            height = self.pixbuf.get_height())
        #draw the pixbuf on to the window
        widget.window.draw_pixbuf(gdk_cxt, self.pixbuf, src_x = 0, src_y = 0, dest_x = 0, dest_y = 0,
            width = -1, height = -1)
        #draw initial lines
        self.recalculate_lines()
        return False
   
    #draws dotted lines to represent where the splits will be
    def draw_lines(self):
        for x in self.x_break:
            self.cairo_cxt.move_to(x, 0)
            self.cairo_cxt.line_to(x, self.allocation.height)
            self.cairo_cxt.stroke()
        for y in self.y_break:
            self.cairo_cxt.move_to(0, y)
            self.cairo_cxt.line_to(self.allocation.width, y)
            self.cairo_cxt.stroke()

    def set_portrait(self, widget):
        if widget.get_active():
            self.portrait = True
            self.redraw()
    def set_landscape(self, widget):
        if widget.get_active():
            self.portrait = False
            self.redraw()

    def set_height(self, widget):
        self.height = int(widget.get_text())
        self.redraw()

    def recalculate_lines(self):
        # if we're in portrait, set the height side accordingly. Otherwise use landscape
        if self.portrait:
            paper_ratio = self.paper_ratio 
        else:
            paper_ratio = 1/self.paper_ratio
        #now assuming that the height side will be fitted to the denominator in paper_ratio
        height_div = self.allocation.height/self.height
        width_div = height_div*paper_ratio
        width_n = int(self.allocation.width/width_div)
        #generate the lists
        self.y_break = [y*height_div for y in range(1,self.height + 1)]
        self.x_break = [x*width_div for x in range(1,width_n + 1)]
        #each time we recalculate, we need to redraw
        self.draw_lines()
    
    #dump the x,y break data to a processing function
    def dump_data(self, func, filename):
        func(self.height, self.portrait, self.pic_name, filename)

    def redraw(self):
        if self.window:
            rect = gtk.gdk.Rectangle(0,0,self.allocation.width,self.allocation.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)


def runDialog(widget, imgD, func):
    fileD = gtk.FileChooserDialog(title="Open..", action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
              buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
    fileD.set_current_folder(".")
    response = fileD.run()
    if response == gtk.RESPONSE_OK:
        f_name = fileD.get_filename()
        imgD.dump_data(func, f_name)
    fileD.destroy()

def save_to_pdf(height, portrait, img_filename, save_filename):
    print "saving..."
    paper_ratio = 8.5/11
    im = Image.open(img_filename)
    #I have no idea how printers work, so let's set the long side of each page to be 1000px
    long_side = 1000
    short_side = int(long_side*paper_ratio)
    #set the target resolution of the rescale, as well as some dimensions that depend on orientation
    if portrait:
        rescale_r = long_side*height/float(im.size[1])
        h_len = long_side
        w_len = short_side
    else:
        rescale_r = short_side*height/float(im.size[1])
        h_len = short_side
        w_len = long_side
    im_rescaled = im.resize(tuple(map((lambda x:int(x*rescale_r)),im.size)), Image.ANTIALIAS)

    #start chopping up the image
    result_images = []
    width_pages = int(im_rescaled.size[0]/w_len) + 1

    for y in range(height):
        for x in range(width_pages):
            w_end = (x+1)*w_len
            if (x+1)*w_len > im_rescaled.size[0]:
                w_end = im_rescaled.size[0]
            im_part = im_rescaled.crop((x*w_len, y*h_len, w_end, (y+1)*h_len))
            if im.mode == "RGBA":
                im_part = Image.composite(im_part,Image.new("RGB",(w_len,h_len),(255,255,255)),im_part.split()[3])
            blank_im = Image.new("RGB",(w_len,h_len),(255,255,255))
            blank_im.paste(im_part,(0,0))
            im_part = blank_im
            result_images.append(im_part)

    #create a ~1cm border around each image
    bordered_images = []
    if portrait:
        w_pad = 34
        h_pad = 44
    else:
        w_pad = 44
        h_pad = 34

    for im in result_images:
        bordered_im = Image.new("RGB",(w_len+w_pad,h_len+h_pad),(255,255,255))
        bordered_im.paste(im,(w_pad/2,h_pad/2))
        bordered_images.append(bordered_im)

    #change to a directory and save everything into it
    for i in range(len(bordered_images)):
        bordered_images[i].save(save_filename+"/"+str(i)+".png")
    print "done"

window = gtk.Window()
img = ImgDisplay(argv[1])

topVBox = gtk.VBox()
upperHBox = gtk.HBox()

#make radio buttons to specify portrait/landscape
port_r_button = gtk.RadioButton(group=None, label="Portrait")
port_r_button.connect("toggled",img.set_portrait)
land_r_button = gtk.RadioButton(group=port_r_button, label="Landscape")
land_r_button.connect("toggled",img.set_landscape)
#make selector for height
height_num = gtk.Entry()
height_num.set_text("")
height_num.set_max_length(2)
height_num.set_width_chars(3)
height_num.connect("activate",img.set_height)
#make a label for height
h_label = gtk.Label()
h_label.set_text("Height:")
#make a button to make the pdf
make_pdf_btn = gtk.Button("Save to directory...")
make_pdf_btn.connect("clicked",runDialog, img, save_to_pdf)
#pack into HBox
upperHBox.pack_start(port_r_button, expand=False)
upperHBox.pack_start(land_r_button)
upperHBox.pack_start(make_pdf_btn)
upperHBox.pack_end(height_num, expand=False, fill=False)
upperHBox.pack_end(h_label, expand=False, fill=False)
#pack into VBox
topVBox.pack_start(upperHBox)
topVBox.pack_start(img)
window.add(topVBox)
window.connect("destroy",gtk.main_quit)
window.show_all()
gtk.main()
