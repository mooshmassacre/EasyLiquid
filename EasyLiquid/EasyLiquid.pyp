# -*- coding: utf-8 -*-
import os
import importlib.util
import sys
import c4d

_spec=importlib.util.spec_from_file_location('liquido_facil_v1_plugin',os.path.join(os.path.dirname(__file__),'plugin.py'))
_module=importlib.util.module_from_spec(_spec)
sys.modules[_spec.name]=_module
_spec.loader.exec_module(_module)

class EasyLiquidCommand(_module.LiquidCommand):
    pass
if __name__=='__main__':
    icon=c4d.bitmaps.BaseBitmap()
    result=icon.InitWith(os.path.join(os.path.dirname(__file__),'res','icon.png'))
    if result[0]!=c4d.IMAGERESULT_OK:icon=None
    if not c4d.plugins.RegisterCommandPlugin(id=_module.PLUGIN_ID,str='EasyLiquid v1.3',info=0,icon=icon,
            help='Continuous waves and motion-responsive liquid.',dat=EasyLiquidCommand()):
        print('EasyLiquid v1.3: Unable to register command; check for plugin ID conflicts.')
