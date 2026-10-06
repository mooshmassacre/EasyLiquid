# -*- coding: utf-8 -*-
import os
import math
import importlib.util
import sys
import c4d

PLUGIN_ID=10691010  # ID provisório da v1 local; substituir por ID Maxon antes de distribuir.
_spec=importlib.util.spec_from_file_location('liquido_facil_v1_engine',os.path.join(os.path.dirname(__file__),'engine.py'))
engine=importlib.util.module_from_spec(_spec)
sys.modules[_spec.name]=engine
_spec.loader.exec_module(engine)
# widget, User Data, label, minimum, maximum, factor (UI / valor interno)
COMMON=[(120,20,'Keep Surface Level',0,1,1)]
CONTINUOUS=[(102,2,'Amplitude (cm)',0,10000,1),(103,3,'Speed (cycles/s)',0,10,1),
 (104,4,'Wavelength (cm)',.001,100000,1),(105,5,'Direction (deg)',-360,360,180/math.pi),
 (106,6,'Secondary Ripples (%)',0,100,100),(107,7,'Edge Lock (%)',0,100,100)]
REACTIVE=[(113,13,'Motion Strength (%)',0,200,100),(114,14,'Wave Rhythm (%)',0,100,100),
 (115,15,'Settling Time (s)',.25,12,1),(116,16,'Ripples (%)',0,100,100),
 (117,17,'Moving Tilt (deg)',0,30,1),(118,18,'Wave Transition (s)',.05,2,1),
 (119,19,'Transition Lead (s)',0,2,1)]

def resolve(doc):
    obj=doc.GetActiveObject()
    if obj is None:return None,None
    return engine.find_mesh(obj)

def visibility(mesh):
    engine.english_controls(mesh)
    mode=int(mesh[c4d.ID_USERDATA,21])
    shown={1,20,21}|(set(range(2,9)) if mode==0 else set(range(13,20)))
    for desc,bc in mesh.GetUserDataContainer():
        bc[c4d.DESC_HIDE]=desc[1].id not in shown
        mesh.SetUserDataContainer(desc,bc)
    mesh.Message(c4d.MSG_UPDATE)


FIELD_ICONS={102:'amplitude',103:'speed',104:'wavelength',105:'tilt',106:'waves',107:'level',
             113:'reactive',114:'speed',115:'settle',116:'waves',117:'tilt',118:'transition',119:'anticipate'}
_BITMAPS={}
def bitmap(name,variant='active'):
    key=(name,variant)
    if key not in _BITMAPS:
        path=os.path.join(os.path.dirname(__file__),'res','icon.png') if name=='plugin' else os.path.join(os.path.dirname(__file__),'res','hud',variant,name+'_32.png')
        bmp=c4d.bitmaps.BaseBitmap()
        _BITMAPS[key]=bmp if bmp.InitWith(path)[0]==c4d.IMAGERESULT_OK else None
    return _BITMAPS[key]

class Symbol(c4d.gui.GeUserArea):
    def __init__(self,name,size=20):
        super().__init__();self.name=name;self.size=size;self.variant='active'
    def GetMinSize(self):return self.size,self.size
    def DrawMsg(self,x1,y1,x2,y2,msg):
        self.OffScreenOn();self.DrawSetPen(c4d.COLOR_BG)
        self.DrawRectangle(x1,y1,x2,y2)
        bmp=bitmap(self.name,self.variant)
        if bmp is not None:
            self.DrawBitmap(bmp,0,0,self.size,self.size,0,0,bmp.GetBw(),bmp.GetBh(),c4d.BMP_NORMAL|c4d.BMP_ALLOWALPHA)
    def change(self,name=None,active=True):
        if name is not None:self.name=name
        self.variant='active' if active else 'neutral';self.Redraw()

class Panel(c4d.gui.GeDialog):
    def symbol(self,name,size=20):
        area=Symbol(name,size);wid=3000+len(self.symbols)
        self.AddUserArea(wid,c4d.BFH_LEFT|c4d.BFV_CENTER,initw=size,inith=size)
        self.AttachUserArea(area,wid);self.symbols.append(area)
        return area
    def button_row(self,wid,name,icon):
        self.GroupBegin(4000+wid,c4d.BFH_SCALEFIT,cols=2,rows=1)
        self.GroupSpace(8,4)
        self.symbol(icon,20)
        self.AddButton(wid,c4d.BFH_SCALEFIT,name=name,inith=0)
        self.GroupEnd()

    def section(self,ident,title):
        self.GroupBegin(ident,c4d.BFH_SCALEFIT,cols=1,rows=0,title=title)
        self.GroupBorder(c4d.BORDER_GROUP_TOP)
        self.GroupBorderSpace(8,6,8,6)
        self.GroupSpace(8,4)

    def CreateLayout(self):
        self.symbols=[]
        self.SetTitle('EasyLiquid • v1.3')
        self.GroupBegin(500,c4d.BFH_SCALEFIT,cols=1,rows=0)
        self.GroupBorderSpace(12,10,12,10)
        self.GroupSpace(0,8)
        self.GroupBegin(501,c4d.BFH_SCALEFIT,cols=2,rows=1)
        self.GroupSpace(10,0)
        self.symbol('plugin',28)
        self.AddStaticText(12,c4d.BFH_LEFT|c4d.BFV_CENTER,name='EasyLiquid  /  Procedural Liquid')
        self.GroupEnd()
        self.section(510,'Setup')
        self.GroupBegin(502,c4d.BFH_SCALEFIT,cols=2,rows=1)
        self.GroupSpace(8,4)
        self.shape_symbol=self.symbol('cylinder')
        self.AddStaticText(10,c4d.BFH_LEFT|c4d.BFV_CENTER,name='Select a cylinder, cube, or liquid mesh.')
        self.GroupEnd()
        self.GroupBegin(503,c4d.BFH_SCALEFIT,cols=2,rows=1)
        self.GroupSpace(8,4)
        self.mode_symbol=self.symbol('reactive')
        self.AddComboBox(100,c4d.BFH_SCALEFIT, inith=0)
        self.AddChild(100,0,'Continuous Waves');self.AddChild(100,1,'Motion Response')
        self.GroupEnd()
        self.button_row(101,'Create / Update Liquid','create')
        self.GroupEnd()
        self.section(511,'Surface')
        self.GroupBegin(504,c4d.BFH_LEFT,cols=4,rows=1)
        self.GroupSpace(8,4)
        self.power_symbol=self.symbol('power');self.AddCheckbox(121,c4d.BFH_LEFT|c4d.BFV_CENTER,0,0,name='Enabled')
        self.level_symbol=self.symbol('level');self.AddCheckbox(120,c4d.BFH_LEFT|c4d.BFV_CENTER,0,0,name='Keep Surface Level (World)')
        self.GroupEnd()
        self.GroupEnd()
        for group,title,fields in [(200,'Continuous Waves',CONTINUOUS),(201,'Motion & Settling',REACTIVE)]:
            self.section(group,title)
            self.GroupBegin(group+20,c4d.BFH_SCALEFIT,cols=4,rows=0)
            self.GroupSpace(8,4)
            for wid,ud,label,low,high,factor in fields:
                self.symbol(FIELD_ICONS[wid],20)
                self.AddStaticText(wid+1000,c4d.BFH_LEFT|c4d.BFV_CENTER,initw=154,name=label)
                self.AddEditNumber(wid,c4d.BFH_LEFT|c4d.BFV_CENTER,initw=54,inith=0)
                self.AddSlider(wid+5000,c4d.BFH_SCALEFIT|c4d.BFV_CENTER,initw=160,inith=0)
            self.GroupEnd()
            self.GroupEnd()
        self.section(512,'Settings')
        self.GroupBegin(513,c4d.BFH_SCALEFIT,cols=2,rows=1)
        self.GroupSpace(12,4)
        self.button_row(122,'Load from Selection','transition')
        self.button_row(123,'Apply Changes','create')
        self.GroupEnd()
        self.AddStaticText(11,c4d.BFH_SCALEFIT,name='Create liquid to get started.')
        self.GroupEnd()
        self.GroupEnd()
        return True
    def refresh_symbols(self):
        self.mode_symbol.change('waves' if self.GetInt32(100)==0 else 'reactive')
        self.power_symbol.change(active=self.GetBool(121))
        self.level_symbol.change(active=self.GetBool(120))
        doc=c4d.documents.GetActiveDocument();obj=doc.GetActiveObject()
        if obj is not None:
            parent=obj.GetUp() if obj.CheckType(c4d.Opolygon) else obj
            self.shape_symbol.change('cube' if parent is not None and parent.CheckType(c4d.Ocube) else 'cylinder')
    def InitValues(self):
        self.SetInt32(100,1);self.SetBool(121,True);self.SetBool(120,False)
        defaults={2:4.,3:.25,4:200.,5:0.,6:.15,7:0.,13:.4,14:.3,15:3.,16:.65,17:10.,18:.35,19:0.}
        for wid,ud,label,low,high,factor in CONTINUOUS+REACTIVE:
            self.SetFloat(wid,defaults[ud]*factor,min=low,max=high,min2=low,max2=high)
            self.SetFloat(wid+5000,defaults[ud]*factor,min=low,max=high,min2=low,max2=high)
        self.groups();self.load(False)
        return True
    def groups(self):
        mode=self.GetInt32(100)
        self.HideElement(200,mode!=0);self.HideElement(201,mode!=1)
        self.LayoutChanged(500)
        self.refresh_symbols()
    def load(self,report=True):
        doc=c4d.documents.GetActiveDocument();mesh,tag=resolve(doc)
        if mesh is None or len(mesh.GetUserDataContainer())!=21:
            if report:self.SetString(11,'Select an EasyLiquid mesh and load again.')
            return False
        self.SetInt32(100,int(mesh[c4d.ID_USERDATA,21]));self.SetBool(121,bool(mesh[c4d.ID_USERDATA,1]));self.SetBool(120,bool(mesh[c4d.ID_USERDATA,20]))
        for wid,ud,label,low,high,factor in CONTINUOUS+REACTIVE:
            self.SetFloat(wid,float(mesh[c4d.ID_USERDATA,ud])*factor,min=low,max=high,min2=low,max2=high)
            self.SetFloat(wid+5000,float(mesh[c4d.ID_USERDATA,ud])*factor,min=low,max=high,min2=low,max2=high)
        self.groups();self.SetString(11,'Selected: '+mesh.GetName());return True
    def apply(self):
        doc=c4d.documents.GetActiveDocument();mesh,tag=resolve(doc)
        if mesh is None or len(mesh.GetUserDataContainer())!=21:
            self.SetString(11,'Create or update the liquid first.');return False
        c4d.StopAllThreads();doc.StartUndo()
        try:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE,mesh)
            mesh[c4d.ID_USERDATA,21]=self.GetInt32(100)
            mesh[c4d.ID_USERDATA,1]=self.GetBool(121);mesh[c4d.ID_USERDATA,20]=self.GetBool(120)
            fields=CONTINUOUS if self.GetInt32(100)==0 else REACTIVE
            for wid,ud,label,low,high,factor in fields:
                mesh[c4d.ID_USERDATA,ud]=max(low,min(high,self.GetFloat(wid)))/factor
            visibility(mesh)
        finally:doc.EndUndo()
        doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE);c4d.EventAdd()
        self.SetString(11,'Changes applied. Animate the original object or its parent Null.');return True
    def Command(self,id,msg):
        fields={field[0]:field for field in CONTINUOUS+REACTIVE}
        base=id-5000 if id-5000 in fields else id
        if base in fields:
            wid,ud,label,low,high,factor=fields[base]
            other=wid if id!=wid else wid+5000
            self.SetFloat(other,self.GetFloat(id),min=low,max=high,min2=low,max2=high)
            return True
        if id==100:self.groups()
        elif id in (120,121):self.refresh_symbols()
        elif id==101:
            doc=c4d.documents.GetActiveDocument()
            if doc.GetActiveObject() is None:
                self.SetString(11,'Select a cylinder, cube, or EasyLiquid mesh.');return True
            mode=self.GetInt32(100);engine.doc=doc;engine.main()
            mesh,tag=resolve(doc)
            if mesh is not None and len(mesh.GetUserDataContainer())==21:
                c4d.StopAllThreads();doc.StartUndo()
                try:
                    doc.AddUndo(c4d.UNDOTYPE_CHANGE,mesh);mesh[c4d.ID_USERDATA,21]=mode;visibility(mesh)
                finally:doc.EndUndo()
                self.load();c4d.EventAdd()
        elif id==122:self.load()
        elif id==123:self.apply()
        return True

class LiquidCommand(c4d.plugins.CommandData):
    panel=None
    def Execute(self,doc):
        if self.panel is None:self.panel=Panel()
        return self.panel.Open(c4d.DLG_TYPE_ASYNC,pluginid=PLUGIN_ID,defaultw=590,defaulth=560)
    def RestoreLayout(self,sec_ref):
        if self.panel is None:self.panel=Panel()
        return self.panel.Restore(pluginid=PLUGIN_ID,secret=sec_ref)
