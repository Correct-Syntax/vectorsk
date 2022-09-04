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

import math
import wx
import cv2
import skia
import moderngl
import numpy as np
from wx import glcanvas

GL_RGBA8 = 0x8058

# Modes
ADD_MODE = 0
EDIT_MODE = 1

# Objects
OBJECT_RECT = 0
OBJECT_TRIANGLE = 1
OBJECT_ELLIPSE = 2
OBJECT_TEXT = 3
OBJECT_IMAGE = 4

# Horizontal align
ALIGN_LEFT 		= 1 << 0 # Default, align text horizontally to left.
ALIGN_CENTER 	= 1 << 1 # Align text horizontally to center.
ALIGN_RIGHT 	= 1 << 2 # Align text horizontally to right.
# Vertical align
ALIGN_TOP 		= 1 << 3 # Align text vertically to top.
ALIGN_MIDDLE	= 1 << 4 # Align text vertically to middle.
ALIGN_BOTTOM	= 1 << 5 # Align text vertically to bottom.
ALIGN_BASELINE	= 1 << 6 # Default, align text vertically to baseline.

# Test an animation
ANIMATION_TEST = False


class BaseObject(object):
    def __init__(self, id, pos):
        self.id = id
        self.pos = pos
        self.size = (1.0, 1.0)
        self.rotation = 0.0
        self.fill_color = (0.0, 1.0, 0.0, 1.0)

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

    def CalcPostSize(self):
        pass

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
    def __init__(self, id, pos):
        BaseObject.__init__(self, id, pos)

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
    def __init__(self, id, pos):
        BaseObject.__init__(self, id, pos)

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
    def __init__(self, id, pos):
        BaseObject.__init__(self, id, pos)

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
    def __init__(self, id, pos):
        BaseObject.__init__(self, id, pos)

        self.text = "Text"
        self.font_size = 50.0
        self.font = skia.Font(skia.Typeface('Arial'), self.font_size)

    def CalcTextSize(self):
        rect = skia.Rect.MakeXYWH(0, 0, 0, 0)
        self.font.measureText(self.text, bounds=rect)
        self.size = (rect.width(), rect.height())

    def CalcRect(self):
        self.bounding_rect = (int(self.pos[0]), int(self.pos[1]), 
                              int(self.size[0]), int(self.size[1]))

    def CalcPostSize(self):
        self.CalcTextSize()
        self.CalculateBounding()

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

        self.DrawText(canvas, self.text, self.pos[0], self.pos[1], 
                      self.font, paint, ALIGN_TOP|ALIGN_MIDDLE)


class Image(BaseObject):
    def __init__(self, id, pos):
        BaseObject.__init__(self, id, pos)

        self.file_path = "C:/Users/Acer/vectorsk/img.jpg"

    def CalcRect(self):
        self.bounding_rect = (int(self.pos[0]), int(self.pos[1]), 
                              int(self.size[0]), int(self.size[1]))

    def Draw(self, canvas):
        paint = skia.Paint()
        image = skia.Image.MakeFromEncoded(
            skia.Data.MakeFromFileName(self.file_path))
        rect = skia.Rect.MakeXYWH(self.pos[0], self.pos[1], 
                                  self.size[0], self.size[1])
        canvas.drawImageRect(image, rect, paint)


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
        self.mode = EDIT_MODE
        self.current_obj_type = OBJECT_RECT

        self.matrix = skia.Matrix()
        self.zoom = 1.0

        # Stress test
        # for i in range(4, 10000):
        #     e = Rectangle(i, (0, i+30))
        #     self.objects.append(e)
        #     e.CalcPostSize()
        #     e.CalculateBounding()

        obj = Rectangle(23, (100, 100))
        obj.size = (200, 200)
        obj.CalculateBounding()
        self.objects.append(obj)

        if ANIMATION_TEST:
            self.p = 0

            self.timer = wx.Timer(self)
            self.timer.Start(0)

            self.obj = Rectangle(23, (0, 0))
            self.obj.size = (200, 200)
            self.obj.CalculateBounding()
            self.objects.append(self.obj)

        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMousewheel)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda x: None)

        if ANIMATION_TEST:
            self.Bind(wx.EVT_TIMER, self.OnTimer)

    def OnTimer(self, event):
        self.obj.pos = (self.p, self.p)
        self.Refresh(False)
        self.p += 10
        if self.p == 1000:
            self.timer.Stop()

    def ToGlobal(self, p):
        '''Convert an (x, y) tuple to global space.'''
        x, y = p
        (gx, gy), = self.matrix.mapPoints([skia.Point(x, y)])
        return wx.Point(int(gx), int(gy))

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

    def DrawOverlay(self, canvas, obj):
        strokePaint = skia.Paint(
            Color=skia.Color(64, 143, 240, 255),
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=1.0
        )
        canvas.drawRect(obj.bounding_rect, strokePaint)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.SetCurrent(self.glcanvas)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()
        #if self.selected is not None:
            #if self.selected.rotation == 0.0:
            #self.selected.CalculateBounding()

            #self.DrawOverlay(self.canvas, self.selected)
            # dc.SetPen(wx.Pen("#438FE6", 2))
            # dc.SetBrush(wx.TRANSPARENT_BRUSH)
            # dc.DrawRectangle(self.selected.bounding_rect)

            # dc.SetPen(wx.Pen("#438FE6", 1))
            # dc.SetBrush(wx.Brush("#fff"))
            # dc.DrawRoundedRectangle(self.selected.overlay_tl, 2)
            # dc.DrawRoundedRectangle(self.selected.overlay_tr, 2)
            # dc.DrawRoundedRectangle(self.selected.overlay_bl, 2)
            # dc.DrawRoundedRectangle(self.selected.overlay_br, 2)

    def OnDraw(self):
        self.SetContextViewport(0, 0, self.Size.width, self.Size.height)
        self.DrawContext()
        self.SwapBuffers()

    def OnLeftDown(self, event):
        pnt = event.GetPosition()
        pnt = self.ToGlobal(pnt)

        if self.mode == ADD_MODE:
            self.selected = self.AddObject(pnt, self.current_obj_type)

        elif self.mode == EDIT_MODE:
            obj = self.ObjectHitTest(pnt)
            if obj is not None:
                self.selected = obj
            else:
                self.selected = None

            if self.selected:
                self.handle = self.HandlesHitTest(pnt)
                # print(self.handle)

        self.last_pnt = pnt
        self.Refresh(False)

    def OnLeftUp(self, event):
        pnt = event.GetPosition()
        pnt = self.ToGlobal(pnt)

        # if self.mode == ADD_MODE:
        #     self.SwitchMode(EDIT_MODE)

        self.last_pnt = pnt

    def OnMotion(self, event):
        pnt = event.GetPosition()
        pnt = self.ToGlobal(pnt)

        if self.mode == ADD_MODE:
            if event.LeftIsDown() and self.selected != None and event.Dragging():
                dpnt = pnt - self.last_pnt
                self.selected.size = (self.selected.size[0] + dpnt[0], 
                                      self.selected.size[1] + dpnt[1])
            self.Refresh(False)
            self.last_pnt = pnt

        elif self.mode == EDIT_MODE:
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

    def OnMousewheel(self, event):
        rotation = event.GetWheelRotation()
        mouse = event.GetPosition()

        if rotation > 1:
            self.zoom = 1.1
        elif rotation < -1:
            self.zoom = 0.9

        # self.matrix.postScale(sx=self.zoom, sy=self.zoom, px=0, py=0)
        # self.matrix.postScale(sx=self.zoom, sy=self.zoom, px=mouse[0], py=mouse[1])
        # self.canvas.setMatrix(self.matrix)

        self.Refresh(False)

    def SetContextViewport(self, x, y, width, height):
        self.ctx.viewport = (x, y, width, height)

    def DrawContext(self):
        self.ctx.clear(255.0, 255.0, 255.0, 0.0)

        for obj in self.objects:
            obj.DrawObject(self.canvas)

        if self.selected is not None:
            self.selected.CalculateBounding()
            self.DrawOverlay(self.canvas, self.selected)

        # self.canvas.clipRect(skia.Rect(0, 0, 600, 600))
        self.surface.flushAndSubmit()

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

    def AddObject(self, pos, obj_type):
        _id = wx.NewIdRef()
        if obj_type == OBJECT_RECT:
            obj = Rectangle(_id, pos)
        elif obj_type == OBJECT_TRIANGLE:
            obj = Triangle(_id, pos)
        elif obj_type == OBJECT_ELLIPSE:
            obj = Ellipse(_id, pos)
        elif obj_type == OBJECT_TEXT:
            obj = Text(_id, pos)
        elif obj_type == OBJECT_IMAGE:
            obj = Image(_id, pos)
        else:
            print("Given object types does not exist")
        self.objects.append(obj)
        obj.CalcPostSize()
        return obj

    def DeleteSelectedObject(self):
        self.objects.remove(self.selected)
        self.selected = None
        self.Refresh(False)

    def SwitchMode(self, mode):
        self.mode = mode

    def SwitchObjectType(self, obj_type):
        self.current_obj_type = obj_type

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


class ContextMenu(wx.Menu):
    def __init__(self, parent):
        super(ContextMenu, self).__init__()
        self.parent = parent

        delete_menu_item = wx.MenuItem(self, -1, 'Delete object')
        self.Append(delete_menu_item)

        self.Bind(wx.EVT_MENU, self.OnDeleteObject, delete_menu_item)

    def OnDeleteObject(self, event):
        self.parent.canvas.DeleteSelectedObject()


class Frame(wx.Frame): 
    def __init__(self, parent, title): 
        super(Frame, self).__init__(parent, title=title, size=(1800, 800))  

        self.SetBackgroundColour(wx.Colour("#eee"))

        sz = wx.BoxSizer(wx.HORIZONTAL)

        self.canvas = DrawCanvas(self, size=(900, 900))

        props_sz = wx.BoxSizer(wx.VERTICAL)

        self.rot_slider = wx.Slider(self, 100, 25, 0, 180, size=(250, -1),
                                    style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        color_btn = wx.Button(self, -1, "Fill color", (50, 50))

        mode = wx.Choice(self, -1, (100, 50), choices=["ADD", "EDIT"])

        obj_types = ["RECTANGLE", "ELLIPSE", "TEXT", "TRIANGLE", "IMAGE"]
        object_type = wx.Choice(self, -1, (100, 50), choices=obj_types)

        props_sz.Add(mode, 0, flag=wx.EXPAND|wx.ALL, border=6)
        props_sz.Add(object_type, 0, flag=wx.EXPAND|wx.ALL, border=6)
        props_sz.Add(self.rot_slider, 0, flag=wx.EXPAND|wx.ALL, border=6)
        props_sz.Add(color_btn, 0, flag=wx.EXPAND|wx.ALL, border=6)
        
        sz.Add(props_sz, 0, flag=wx.EXPAND|wx.ALL, border=20)
        sz.Add(self.canvas, 0, flag=wx.EXPAND|wx.ALL)
        self.SetSizer(sz)

        self.rot_slider.Bind(wx.EVT_SLIDER, self.OnChangeRot)
        color_btn.Bind(wx.EVT_BUTTON, self.OnColorButton)
        mode.Bind(wx.EVT_CHOICE, self.OnChangeMode)
        object_type.Bind(wx.EVT_CHOICE, self.OnChangeObjectType)
        self.canvas.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

        self.Maximize()

    def OnRightDown(self, event):
        self.canvas.PopupMenu(ContextMenu(self.canvas), event.GetPosition())

    def OnChangeMode(self, event):
        mode = event.GetString()
        if mode == "ADD":
            mode = ADD_MODE
        elif mode == "EDIT":
            mode = EDIT_MODE
        self.canvas.SwitchMode(mode)
        event.Skip()

    def OnChangeObjectType(self, event):
        obj_type = event.GetString()
        if obj_type == "RECTANGLE":
            obj_type = OBJECT_RECT
        elif obj_type == "ELLIPSE":
            obj_type = OBJECT_ELLIPSE
        elif obj_type == "TEXT":
            obj_type = OBJECT_TEXT
        elif obj_type == "TRIANGLE":
            obj_type = OBJECT_TRIANGLE
        elif obj_type == "IMAGE":
            obj_type = OBJECT_IMAGE
        self.canvas.SwitchObjectType(obj_type)
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
