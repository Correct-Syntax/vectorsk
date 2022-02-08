# ----------------------------------------------------------------------------
# VectorSK Copyright 2022 Noah Rahm
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ----------------------------------------------------------------------------

import wx
import cv2
import skia
import moderngl
import numpy as np
from wx import glcanvas

GL_RGBA8 = 0x8058

# Horizontal align
ALIGN_LEFT 		= 1 << 0 # Default, align text horizontally to left.
ALIGN_CENTER 	= 1 << 1 # Align text horizontally to center.
ALIGN_RIGHT 	= 1 << 2 # Align text horizontally to right.
# Vertical align
ALIGN_TOP 		= 1 << 3 # Align text vertically to top.
ALIGN_MIDDLE	= 1 << 4 # Align text vertically to middle.
ALIGN_BOTTOM	= 1 << 5 # Align text vertically to bottom.
ALIGN_BASELINE	= 1 << 6 # Default, align text vertically to baseline.


class BaseObject(object):
    def __init__(self, id):
        self.id = id
        self.pos = (100.0, 100.0)
        self.size = (50.0, 50.0)
        self.rotation = 0.0
        self.fill_color = (0.0, 0.2, 1.0, 1.0)

    def CalculateBounding(self):
        self.CalcHandles()
        self.CalcRect()

    def CalcRect(self):
        self.bounding_rect = (int(self.pos[0]), int(self.pos[1]), 
                              int(self.size[0]), int(self.size[1]))

    def CalcHandles(self):
        self.overlay_tl = (int(self.pos[0]-6), 
                           int(self.pos[1]-6), 
                           10, 10)
        self.overlay_tr = (int(self.pos[0]+self.size[0]-6), 
                           int(self.pos[1]-6), 
                           10, 10)
        self.overlay_bl = (int(self.pos[0]-6), 
                           int(self.pos[1]+self.size[1]-6), 
                           10, 10)
        self.overlay_br = (int(self.pos[0]+self.size[0]-6), 
                           int(self.pos[1]+self.size[1]-6), 
                           10, 10)

    def DrawObject(self, canvas):
        if self.rotation != 0.0:
            canvas.save()
            canvas.rotate(self.rotation, 
                          self.pos[0]+(self.size[0]/2), 
                          self.pos[1]+(self.size[1]/2.0))
            self.Draw(canvas)
            canvas.restore()
        else:
            self.Draw(canvas)


class Ellipse(BaseObject):
    def __init__(self, id):
        BaseObject.__init__(self, id)
        
        self.CalculateBounding()

    def Draw(self, canvas):
        paint = skia.Paint(AntiAlias=True,
                           Color=skia.Color4f(self.fill_color),
                           StrokeCap=skia.Paint.kButt_Cap,
                           StrokeJoin=skia.Paint.kMiter_Join,
                           StrokeMiter=0,
                           StrokeWidth=0,
                           Style=skia.Paint.kFill_Style)
        
        canvas.drawOval(skia.Rect.MakeXYWH(self.pos[0], self.pos[1], 
                        self.size[0], self.size[1]), paint)


class Rectangle(BaseObject):
    def __init__(self, id):
        BaseObject.__init__(self, id)

        self.pos = (150.0, 30.0)
        self.size = (160.0, 190.0)

        self.CalculateBounding()

    def Draw(self, canvas):
        paint = skia.Paint(AntiAlias=True,
                           Color=skia.Color4f(self.fill_color),
                           StrokeCap=skia.Paint.kButt_Cap,
                           StrokeJoin=skia.Paint.kMiter_Join,
                           StrokeMiter=0,
                           StrokeWidth=0,
                           Style=skia.Paint.kStrokeAndFill_Style)
        
        canvas.drawRoundRect(skia.Rect.MakeXYWH(self.pos[0], self.pos[1], 
                                                self.size[0], self.size[1]), 
                             rx=12.0, ry=12.0, paint=paint)


class Triangle(BaseObject):
    def __init__(self, id):
        BaseObject.__init__(self, id)

        self.pos = (100.0, 50.0)
        self.size = (200.0, 160.0)

        self.CalculateBounding()

    def Draw(self, canvas):
        paint = skia.Paint(AntiAlias=True,
                           Color=skia.Color4f(self.fill_color),
                           StrokeCap=skia.Paint.kButt_Cap,
                           StrokeJoin=skia.Paint.kMiter_Join,
                           StrokeMiter=0,
                           StrokeWidth=0,
                           Style=skia.Paint.kStrokeAndFill_Style)
    
        p1 = skia.Point(self.pos[0]+(self.size[0]/2), self.pos[1])
        p2 = skia.Point(self.pos[0], self.pos[1]+self.size[1])
        p3 = skia.Point(self.pos[0]+self.size[0], self.pos[1]+self.size[1])

        tri = skia.Vertices(skia.Vertices.kTriangles_VertexMode,[p1,p2,p3])
        canvas.drawVertices(tri, paint)


class Text(BaseObject):
    def __init__(self, id):
        BaseObject.__init__(self, id)

        self.pos = (200.0, 400.0)
        self.size = (40.0, 40.0)
        self.text = "hello there"
        self.font_size = 70.0
        self.font = skia.Font(skia.Typeface('Arial'), self.font_size)
        
        self.CalcTextSize()
        self.CalculateBounding()

    def CalcTextSize(self):
        rect = skia.Rect.MakeXYWH(0, 0, 0, 0)
        self.font.measureText(self.text, bounds=rect)

        self.size = (rect.width(), rect.height())

    def CalcRect(self):
        self.bounding_rect = (int(self.pos[0]), int(self.pos[1]), 
                              int(self.size[0]), int(self.size[1]))

    def DrawText(self, canvas, txt, x, y, font, paint, flags):
        # Get bounds of txt
        rect = skia.Rect.MakeXYWH(0, 0, 0, 0)
        font.measureText(txt, bounds=rect)
        
        px = 0.0
        py = 0.0
        if ALIGN_LEFT & flags:
            px = rect.x()
        elif ALIGN_CENTER & flags:
            px = rect.width()/2.0
        elif ALIGN_RIGHT & flags:
            px = rect.width()

        if ALIGN_TOP & flags:
            py = rect.y()
        elif ALIGN_MIDDLE & flags:
            py = -rect.height()/2.0
        elif ALIGN_BOTTOM & flags:
            py = 0.0
        elif ALIGN_BASELINE & flags:
            pass
        
        canvas.drawString(txt, x-px, y-py, font, paint)

    def Draw(self, canvas):
        paint = skia.Paint(AntiAlias=True,
                           Color=skia.Color4f(self.fill_color),
                           StrokeCap=skia.Paint.kButt_Cap,
                           StrokeJoin=skia.Paint.kMiter_Join,
                           StrokeMiter=0,
                           StrokeWidth=0,
                           Style=skia.Paint.kStrokeAndFill_Style)

        # canvas.clipRect(skia.Rect(
        #                     self.pos[0], 
        #                     self.pos[1], 
        #                     self.pos[0]+self.size[0], 
        #                     self.pos[1]+self.size[1]))

        self.DrawText(canvas, self.text, self.pos[0], self.pos[1], 
                      self.font, paint, ALIGN_TOP|ALIGN_MIDDLE)


class DrawCanvas(glcanvas.GLCanvas):
    def __init__(self, parent, size):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size)
        self.size = None
        self.init = False
        self.ctx = None
        self.glcanvas = glcanvas.GLContext(self)

        self.objects = []
        self.selected = None
        self.last_pnt = None
        self.handle = None

        # Add objects
        c2 = Rectangle(3)
        self.objects.append(c2)
        t = Text(2)
        self.objects.append(t)
        c = Ellipse(1)
        self.objects.append(c)
        tri = Triangle(4)
        self.objects.append(tri)

        # Stress test
        # for i in range(4, 8000):
        #     e = Ellipse(i)
        #     self.objects.append(e)

        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda x: None)

    def OnEraseBackground(self, event):
        pass  # Do nothing, to avoid flashing on MSW.

    def OnSize(self, event):
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        size = self.size = self.GetClientSize()
        self.SetCurrent(self.glcanvas)
        if not self.ctx is None:
            self.SetContextViewport(0, 0, self.Size.width, self.Size.height)

    def InitGL(self):
        self.ctx = moderngl.create_context()
        context = skia.GrDirectContext.MakeGL()
        backend_render_target = skia.GrBackendRenderTarget(
            self.size[0],
            self.size[1],
            0,  # sampleCnt
            0,  # stencilBits
            skia.GrGLFramebufferInfo(0, GL_RGBA8))
        self.surface = skia.Surface.MakeFromBackendRenderTarget(
            context, backend_render_target, skia.kBottomLeft_GrSurfaceOrigin,
            skia.kRGBA_8888_ColorType, skia.ColorSpace.MakeSRGB())
        self.canvas = self.surface.getCanvas()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.SetCurrent(self.glcanvas)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()
        if self.selected is not None:
            self.selected.CalculateBounding()

            dc.SetPen(wx.Pen("#438FE6", 2))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(self.selected.bounding_rect)

            dc.SetPen(wx.Pen("#438FE6", 1))
            dc.SetBrush(wx.Brush("#fff"))
            dc.DrawRoundedRectangle(self.selected.overlay_tl, 2)
            dc.DrawRoundedRectangle(self.selected.overlay_tr, 2)
            dc.DrawRoundedRectangle(self.selected.overlay_bl, 2)
            dc.DrawRoundedRectangle(self.selected.overlay_br, 2)

    def OnDraw(self):
        self.SetContextViewport(0, 0, self.Size.width, self.Size.height)
        self.DrawContext()
        self.SwapBuffers()

    def OnLeftDown(self, event):
        pnt = event.GetPosition()
        # print(pnt, "<<")

        obj = self.ObjectHitTest(pnt)
        # print(obj, "///object///")
        if obj is not None:
            self.selected = obj
        # else:
        #     self.selected = None

        if self.selected:
            self.handle = self.HandlesHitTest(pnt)
            # print(self.handle)

        self.last_pnt = pnt
        self.Refresh(False)

    def OnLeftUp(self, event):
        pnt = event.GetPosition()

        self.last_pnt = pnt

    def OnMotion(self, event):
        pnt = event.GetPosition()

        if event.LeftIsDown() and self.selected != None and event.Dragging():
            if self.handle is not None:

                dpnt = pnt - self.last_pnt
                self.selected.size = (self.selected.size[0] + dpnt[0], 
                                      self.selected.size[1] + dpnt[1])

            else:
                dpnt = self.selected.pos + pnt - self.last_pnt
                self.selected.pos = dpnt
            self.Refresh(False)
        self.last_pnt = pnt

        if self.selected:
            handle = self.HandlesHitTest(pnt)
            if handle == "tl":
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZENWSE))
            elif handle == "tr":
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZENESW))
            elif handle == "bl":
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZENESW))
            elif handle == "br":
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZENWSE))
            else:
                self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def ObjectHitTest(self, pos):
        for obj in self.objects:
            rect = skia.Rect(obj.bounding_rect)               
            if rect.contains(pos[0], pos[1]) is True:
                return obj

    def HandlesHitTest(self, pos):
        mouse_rect = wx.Rect(pos[0], pos[1], 2, 2)
        if mouse_rect.Intersects(self.selected.overlay_tl):
            return "tl"
        elif mouse_rect.Intersects(self.selected.overlay_tr):
            return "tr"
        elif mouse_rect.Intersects(self.selected.overlay_bl):
            return "bl"
        elif mouse_rect.Intersects(self.selected.overlay_br):
            return "br"
        else:
            # print("No handle")
            return None

    def SetContextViewport(self, x, y, width, height):
        self.ctx.viewport = (x, y, width, height)

    def DrawContext(self):
        self.ctx.clear(255.0, 255.0, 255.0, 0.0)

        for obj in self.objects:
            obj.DrawObject(self.canvas)

        # self.canvas.clipRect(skia.Rect(0, 0, 600, 600))
        self.surface.flushAndSubmit()

    def SetFillColor(self, color):
        if self.selected:
            self.selected.fill_color = color
        else:
            print("Please select an object first")
        self.Refresh(False)

    def SetRotation(self, rot):
        if self.selected:
            self.selected.rotation = rot
        else:
            print("Please select an object first")
        self.Refresh(False)

class Frame(wx.Frame): 
    def __init__(self, parent, title): 
        super(Frame, self).__init__(parent, title=title, size=(1800, 800))  

        self.SetBackgroundColour(wx.Colour("#eee"))

        sz = wx.BoxSizer(wx.HORIZONTAL)

        self.canvas = DrawCanvas(self, size=(900, 900))

        props_sz = wx.BoxSizer(wx.VERTICAL)
        self.slider_x = wx.Slider(
            self, 100, 25, 1, 100, size=(250, -1),
            style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        self.rot_slider = wx.Slider(
            self, 100, 25, 0, 180, size=(250, -1),
            style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        color_btn = wx.Button(self, -1, "Fill color", (50, 50))

        props_sz.Add(self.slider_x, 0, flag=wx.EXPAND|wx.ALL)
        props_sz.Add(self.rot_slider, 0, flag=wx.EXPAND|wx.ALL)
        props_sz.Add(color_btn, 0, flag=wx.EXPAND|wx.ALL)

        sz.Add(props_sz, 0, flag=wx.EXPAND|wx.ALL, border=20)
        sz.Add(self.canvas, 0, flag=wx.EXPAND|wx.ALL)
        self.SetSizer(sz)

        self.Maximize()

        # self.slider_x.Bind(wx.EVT_SLIDER, self.OnChangeX)
        self.rot_slider.Bind(wx.EVT_SLIDER, self.OnChangeRot)
        color_btn.Bind(wx.EVT_BUTTON, self.OnColorButton)

    def OnChangeX(self, event):
        self.canvas.SetXPos(self.slider_x.GetValue())
        event.Skip()

    def OnChangeRot(self, event):
        self.canvas.SetRotation(float(self.rot_slider.GetValue()))
        event.Skip()

    def OnColorButton(self, event):
        dlg = wx.ColourDialog(self)

        dlg.GetColourData().SetChooseFull(True)

        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetColourData()

            color = data.GetColour().Get()
            self.canvas.SetFillColor((float(color[0]/255.0), float(color[1]/255.0), 
                                      float(color[2]/255.0), 1.0))
            # print('You selected: %s\n' % str(color))

        dlg.Destroy()
		

ex = wx.App() 
win = Frame(None, "VectorSK") 
win.Show(True)
ex.MainLoop()