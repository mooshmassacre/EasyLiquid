# -*- coding: utf-8 -*-
"""Liquido Facil — Script Manager, Cinema 4D 2024+.
Selecione o cilindro parametrico ou a malha da versao anterior e Execute uma vez.
Le automaticamente as curvas de Position da malha e de todos os pais.
Keyframes/tangentes alterados atualizam a reacao sem bake ou reexecucao.
Rotacao e escala devem permanecer constantes na hierarquia.
Sem simulacao fisica. Sem dependencias externas ou plugins.
"""
import ast
import math
import traceback
import c4d

VERSAO_SCRIPT = "3.7 - topo nivelado no mundo"
SEGMENTOS = 96
ANEIS_TOPO = 24
SEGMENTOS_ALTURA = 16
MARCADOR = 10691001

def orient(x, y, z, axis):
    if axis == c4d.PRIM_AXIS_XP: return c4d.Vector(y, -x, z)
    if axis == c4d.PRIM_AXIS_XN: return c4d.Vector(-y, x, z)
    if axis == c4d.PRIM_AXIS_YN: return c4d.Vector(x, -y, -z)
    if axis == c4d.PRIM_AXIS_ZP: return c4d.Vector(x, -z, y)
    if axis == c4d.PRIM_AXIS_ZN: return c4d.Vector(x, z, -y)
    return c4d.Vector(x, y, z)


def geometry(radius, height, axis):
    rest, faces = [], []
    n, h, rings = SEGMENTOS, SEGMENTOS_ALTURA, ANEIS_TOPO
    # Laterais: aneis compartilhados com topo e fundo, sem costuras.
    for j in range(h + 1):
        t = j / float(h)
        for i in range(n):
            a = 2.0 * math.pi * i / n
            rest.append((radius * math.cos(a), height * (t - 0.5),
                         radius * math.sin(a), t ** 4))
    for j in range(h):
        for i in range(n):
            q = (i + 1) % n
            faces.append((j*n+i, (j+1)*n+i, (j+1)*n+q, j*n+q))
    outer = h * n
    for j in range(1, rings):
        inner = len(rest)
        r = radius * (1.0 - j / float(rings))
        for i in range(n):
            a = 2.0 * math.pi * i / n
            rest.append((r * math.cos(a), height * 0.5, r * math.sin(a), 1.0))
        for i in range(n):
            q = (i + 1) % n
            faces.append((outer+i, inner+i, inner+q, outer+q))
        outer = inner
    center = len(rest)
    rest.append((0.0, height*0.5, 0.0, 1.0))
    for i in range(n):
        faces.append((outer+i, center, outer+(i+1)%n))
    bottom = len(rest)
    rest.append((0.0, -height*0.5, 0.0, 0.0))
    for i in range(n):
        faces.append((i, (i+1)%n, bottom))
    obj = c4d.PolygonObject(len(rest), len(faces))
    obj.SetAllPoints([orient(x, y, z, axis) for x, y, z, w in rest])
    for i, f in enumerate(faces):
        obj.SetPolygon(i, c4d.CPolygon(*f))
    obj.Message(c4d.MSG_UPDATE)
    return obj, rest


def control(obj, name, dtype, value, unit=None, minimum=None, maximum=None):
    bc = c4d.GetCustomDataTypeDefault(dtype)
    bc[c4d.DESC_NAME] = name
    bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_ON
    if unit is not None: bc[c4d.DESC_UNIT] = unit
    if minimum is not None: bc[c4d.DESC_MIN] = minimum
    if maximum is not None: bc[c4d.DESC_MAX] = maximum
    desc = obj.AddUserData(bc)
    obj[desc] = value


# Codigo embutido na tag: nenhum acesso a arquivos apos salvar a cena.
TAG_CODE = '\nimport math\nimport c4d\nREST = __REST__\nAXIS = __AXIS__\nHEIGHT = __HEIGHT__\nRADIUS = __RADIUS__\nINTERNAL_HZ = 120.0\nMAX_SAMPLES = 48000\n_cache = None\n_detail_cache = None\n_spatial_cache = None\n_blend_cache = None\n\ndef orient(x, y, z):\n    if AXIS == c4d.PRIM_AXIS_XP: return c4d.Vector(y, -x, z)\n    if AXIS == c4d.PRIM_AXIS_XN: return c4d.Vector(-y, x, z)\n    if AXIS == c4d.PRIM_AXIS_YN: return c4d.Vector(x, -y, -z)\n    if AXIS == c4d.PRIM_AXIS_ZP: return c4d.Vector(x, -z, y)\n    if AXIS == c4d.PRIM_AXIS_ZN: return c4d.Vector(x, z, -y)\n    return c4d.Vector(x, y, z)\n\ndef transition(dt, frequency, damping):\n    """Matriz exata de mola amortecida para forca constante (sem Euler)."""\n    omega = 2.0 * math.pi * frequency\n    gamma = damping * omega\n    discriminant = omega * omega - gamma * gamma\n    e = math.exp(-gamma * dt)\n    if abs(discriminant) < 1e-10:\n        co, si = 1.0, dt\n    elif discriminant > 0:\n        wd = math.sqrt(discriminant)\n        co, si = math.cos(wd * dt), math.sin(wd * dt) / wd\n    else:\n        wd = math.sqrt(-discriminant)\n        # Forma exponencial evita overflow para extrapolacao longa.\n        a, b = math.exp((-gamma + wd)*dt), math.exp((-gamma - wd)*dt)\n        ec, es = (a+b)*0.5, (a-b)/(2.0*wd)\n        return ec+gamma*es, es, -omega*omega*es, ec-gamma*es\n    return e*(co+gamma*si), e*si, -omega*omega*e*si, e*(co-gamma*si)\n\ndef step(q, v, target, matrix):\n    a,b,c,d = matrix\n    offset = q-target\n    return target+a*offset+b*v, c*offset+d*v\n\ndef xyz(v):\n    return (v.x,v.y,v.z)\n\ndef motion_hierarchy(obj):\n    """Le curvas de Position. Rotacao/escala da hierarquia devem ser constantes."""\n    hierarchy,signature = [],[]\n    while obj is not None:\n        matrix = c4d.Matrix(obj.GetMl())\n        frozen = obj.GetFrozenMln()\n        relative = obj.GetRelPos()\n        base = matrix.off-frozen.MulV(relative)\n        curves=[]\n        constants=[]\n        for index,component in enumerate((c4d.VECTOR_X,c4d.VECTOR_Y,c4d.VECTOR_Z)):\n            desc = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION,c4d.DTYPE_VECTOR,0),\n                             c4d.DescLevel(component,c4d.DTYPE_REAL,0))\n            track = obj.FindCTrack(desc)\n            curve = track.GetCurve() if track is not None else None\n            if curve is not None and curve.GetKeyCount()>0:\n                curves.append(curve)\n                constants.append(0.0)\n                signature.append((track,curve.GetDirty(c4d.DIRTYFLAGS_DATA | c4d.DIRTYFLAGS_CHILDREN),\n                                  track.GetDirty(c4d.DIRTYFLAGS_DATA | c4d.DIRTYFLAGS_CHILDREN),\n                                  curve.GetKeyCount()))\n            else:\n                curves.append(None)\n                constants.append(xyz(relative)[index])\n                signature.append((\'constant\',constants[-1]))\n        signature.append(tuple(round(v,10) for vec in (matrix.v1,matrix.v2,matrix.v3,\n                                  base,frozen.v1,frozen.v2,frozen.v3) for v in xyz(vec)))\n        hierarchy.append((matrix,frozen,base,tuple(curves),tuple(constants)))\n        obj = obj.GetUp()\n    return hierarchy,tuple(signature)\n\ndef position_at(time,hierarchy,fps):\n    point = c4d.Vector(0.0)\n    bt = c4d.BaseTime(time)\n    # Parte do centro da malha e sobe ate a raiz, acumulando PSR dos pais.\n    for matrix,frozen,base,curves,constants in hierarchy:\n        values = [curve.GetValue(bt,fps) if curve is not None else constant\n                  for curve,constant in zip(curves,constants)]\n        offset = base+frozen.MulV(c4d.Vector(*values))\n        point = matrix.MulV(point)+offset\n    return point\n\ndef drive(acceleration,gain):\n    limit=HEIGHT*.16\n    return limit*math.tanh(-.005*gain*acceleration/limit)\n\n\ndef movement_mix(forces,gain):\n    if len(forces)>2: return forces[2]\n    height=math.hypot(drive(forces[0],gain),drive(forces[1],gain))\n    return 1.0-math.exp(-height/max(.01,HEIGHT*.008))\n\ndef motion_matrix(dt,frequency,damping,forces,gain):\n    mix=movement_mix(forces,gain)\n    return transition(dt,frequency,damping+(max(1.0,damping)-damping)*mix)\n\ndef response(gain,frequency,damping,obj):\n    global _cache\n    hierarchy,signature = motion_hierarchy(obj)\n    fps = doc.GetFps()\n    t0,t1 = doc.GetMinTime().Get(),doc.GetMaxTime().Get()\n    dt = 1.0/INTERNAL_HZ\n    count = max(3,int(math.ceil((t1-t0)/dt))+1)\n    if count>MAX_SAMPLES:\n        raise ValueError(\'Intervalo muito longo: reduza o intervalo do projeto (max. 400 segundos).\')\n    anticipation=min(2.0,max(0.0,float(obj[c4d.ID_USERDATA,19])))\n    key = (gain,frequency,damping,fps,t0,t1,signature,anticipation)\n    if _cache is not None and _cache[0]==key: return _cache[1]\n    positions = [position_at(t0+i*dt,hierarchy,fps) for i in range(count)]\n    mg = obj.GetMg()\n    if abs(mg.v1.Dot(mg.v2.Cross(mg.v3)))<1e-12:\n        raise ValueError(\'Escala zero na hierarquia do liquido.\')\n    inverse = ~mg\n    bx,bz = orient(1.0,0.0,0.0),orient(0.0,0.0,1.0)\n    # Um seguidor virtual critico transforma QUALQUER curva de Position\n    # em movimento continuo. Nao deriva numericamente keys/teletransportes.\n    # O filtro altera apenas o liquido: o copo mantem a animacao original.\n    input_omega=2.0*math.pi*8.0\n    input_matrix=transition(dt*.5,8.0,1.0)\n    previous=xyz(positions[0])\n    follower=list(previous)\n    velocity=[0.0,0.0,0.0]\n    forces=[]\n    for i in range(count-1):\n        current=xyz(positions[i+1])\n        acceleration=[]\n        for axis in range(3):\n            target_position=(previous[axis]+current[axis])*.5\n            q,v=step(follower[axis],velocity[axis],target_position,input_matrix)\n            acceleration.append(input_omega*input_omega*(target_position-q)-2.0*input_omega*v)\n            follower[axis],velocity[axis]=step(q,v,target_position,input_matrix)\n        local=inverse.MulV(c4d.Vector(*velocity))*35.0\n        forces.append((local.Dot(bx),local.Dot(bz)))\n        previous=current\n    forces.append((0.0,0.0))\n    # A liberacao depende da perda relativa de velocidade, nao de atingir zero.\n    # O lookahead atua no motor e na forma: o copo conserva seus keys.\n    original=forces\n    speeds=[math.hypot(*force) for force in original]\n    forces=[]\n    lookahead=anticipation/dt\n    window=max(1,int(.5/dt))\n    limit=HEIGHT*.16\n    for i,force in enumerate(original):\n        future=min(len(original)-1,i+int(lookahead))\n        u=lookahead-int(lookahead)\n        next_index=min(len(original)-1,future+1)\n        upcoming=tuple(a+(b-a)*u for a,b in zip(original[future],original[next_index]))\n        recent=speeds[max(0,i-window):i+1]\n        peak=max(recent)\n        # Nao apaga impulsos curtos/Step ao olhar uma parada futura.\n        sustained=(sum(recent)/float(window+1))/peak if peak>1e-9 else 0.0\n        weight=max(0.0,min(1.0,(sustained-.2)/.4))\n        weight=weight*weight*(3.0-2.0*weight)\n        chosen=tuple(a+(b-a)*weight for a,b in zip(force,upcoming)) if math.hypot(*upcoming)<speeds[i] else force\n        speed=math.hypot(*chosen)\n        ratio=min(1.0,speed/peak) if peak>1e-9 else 0.0\n        release=ratio*ratio\n        # Reescala DEPOIS da saturacao para liberar mesmo com Forca alta.\n        target=[drive(value,gain)*release for value in chosen]\n        equivalent=tuple(-limit*math.atanh(max(-.999999,min(.999999,value/limit)))/(.005*gain)\n                         for value in target)\n        mix=movement_mix(chosen,gain)*release\n        forces.append(equivalent+(mix,))\n    matrix=transition(dt,frequency,damping)\n    states=[(0.0,0.0,0.0,0.0)]\n    qx=qz=vx=vz=0.0\n    for i in range(1,count):\n        fx=drive(forces[i-1][0],gain)\n        fz=drive(forces[i-1][1],gain)\n        matrix=motion_matrix(dt,frequency,damping,forces[i-1],gain)\n        qx,vx=step(qx,vx,fx,matrix)\n        qz,vz=step(qz,vz,fz,matrix)\n        states.append((qx,qz,vx,vz))\n    result = (states,forces,t0,dt)\n    _cache = (key,result)\n    return result\n\ndef at_state(time,states,gain,frequency,damping,forces,t0,dt):\n    f=(time-t0)/dt\n    if f<=0: return 0.0,0.0,0.0,0.0\n    last=len(states)-1\n    if f>=last:\n        qx,qz,vx,vz=states[-1]\n        matrix=transition((f-last)*dt,frequency,damping)\n        qx,vx=step(qx,vx,0.0,matrix)\n        qz,vz=step(qz,vz,0.0,matrix)\n    else:\n        i=int(math.floor(f))\n        qx,qz,vx,vz=states[i]\n        matrix=motion_matrix((f-i)*dt,frequency,damping,forces[i],gain)\n        fx=drive(forces[i][0],gain)\n        fz=drive(forces[i][1],gain)\n        qx,vx=step(qx,vx,fx,matrix)\n        qz,vz=step(qz,vz,fz,matrix)\n    return qx,qz,vx,vz\n\ndef at_time(time,states,gain,frequency,damping,forces,t0,dt):\n    return at_state(time,states,gain,frequency,damping,forces,t0,dt)[:2]\n\n\ndef detail_response(states,forces,dt,gain,frequency,damping):\n    """Segundo modo com seu proprio atraso, para dobrar o topo em vez de so inclinar."""\n    global _detail_cache\n    detail_frequency = min(12.0,frequency*1.85)\n    detail_damping = min(2.0,max(.12,damping*1.2))\n    detail_gain = gain*.65\n    key = (id(states),detail_gain,detail_frequency,detail_damping,dt)\n    if _detail_cache is not None and _detail_cache[0]==key:\n        return _detail_cache[1],detail_gain,detail_frequency,detail_damping\n    matrix=transition(dt,detail_frequency,detail_damping)\n    result=[(0.0,0.0,0.0,0.0)]\n    qx=qz=vx=vz=0.0\n    for i in range(1,len(forces)):\n        fx=drive(forces[i-1][0],detail_gain)\n        fz=drive(forces[i-1][1],detail_gain)\n        matrix=motion_matrix(dt,detail_frequency,detail_damping,forces[i-1],detail_gain)\n        qx,vx=step(qx,vx,fx,matrix)\n        qz,vz=step(qz,vz,fz,matrix)\n        result.append((qx,qz,vx,vz))\n    _detail_cache=(key,result)\n    return result,detail_gain,detail_frequency,detail_damping\n\n\ndef wave_blend(time,states,forces,t0,dt,gain,duration,anticipation=0.0):\n    global _blend_cache\n    key=(states,gain,duration)\n    if _blend_cache is None or _blend_cache[0][0] is not states or _blend_cache[0][1:]!=key[1:]:\n        # Envelope independente da ordem da timeline. Filtra as duas fases.\n        alpha=1.0-math.exp(-dt/max(.02,duration/3.0))\n        values=[0.0]\n        for force in forces[:-1]:\n            target=1.0-movement_mix(force,gain)\n            values.append(values[-1]+alpha*(target-values[-1]))\n        _blend_cache=(key,values)\n    values=_blend_cache[1]\n    def sample(at):\n        f=max(0.0,(at-t0)/dt)\n        i=min(len(values)-1,int(f))\n        if i==len(values)-1:return values[i]\n        u=f-i\n        return values[i]+u*(values[i+1]-values[i])\n    current=sample(time)\n    upcoming=sample(time) # antecipacao ja aplicada ao motor\n    # Antecipa somente a liberacao; nao adianta o inicio do deslocamento.\n    return max(current,upcoming)\n\n\ndef disk_mean(k):\n    # Media espacial por area, para o termo cosseno nao elevar a superficie inteira.\n    total=0.0\n    for j in range(12):\n        radius=math.sqrt((j+.5)/12.0)\n        for i in range(48):\n            x=radius*math.cos(2.0*math.pi*(i+.5)/48.0)\n            total+=math.cos(k*x)\n    return total/(12.0*48.0)\n\ndef spatial_basis():\n    global _spatial_cache\n    if _spatial_cache is not None: return _spatial_cache\n    k1,k2=math.pi*.55,math.pi*1.5\n    mean1,mean2=disk_mean(k1),disk_mean(k2)\n    entries=[]\n    for x,y,z,weight in REST:\n        xx,zz=x/RADIUS,z/RADIUS\n        # Seno e cosseno: crista se desloca enquanto o balanco troca de sentido.\n        entries.append((math.sin(k1*xx),math.cos(k1*xx)-mean1,\n                        math.sin(k1*zz),math.cos(k1*zz)-mean1,\n                        math.sin(k2*xx),math.cos(k2*xx)-mean2,\n                        math.sin(k2*zz),math.cos(k2*zz)-mean2))\n    _spatial_cache=entries\n    return entries\n\ndef world_slopes(obj,enabled):\n    if not enabled:return 0.0,0.0\n    mg=obj.GetMg()\n    up=mg.MulV(orient(0.0,1.0,0.0)).y\n    magnitude=abs(up)\n    if magnitude<1e-6:return 0.0,0.0\n    fade=min(1.0,magnitude/.15)\n    fade=fade*fade*(3.0-2.0*fade)\n    return (-mg.MulV(orient(1.0,0.0,0.0)).y/up*fade,\n            -mg.MulV(orient(0.0,0.0,1.0)).y/up*fade)\n\n\ndef reactive_main():\n    obj=op.GetObject()\n    if obj is None or not obj.CheckType(c4d.Opolygon): return\n    if obj.GetPointCount()!=len(REST): return\n    enabled=bool(obj[c4d.ID_USERDATA,1])\n    level=bool(obj[c4d.ID_USERDATA,20])\n    sx,sz=world_slopes(obj,level)\n    # Quatro controles em linguagem de uso; conversao interna automatica.\n    gain=min(5.0,max(0.0,float(obj[c4d.ID_USERDATA,13])*2.5))\n    rhythm=min(1.0,max(0.0,float(obj[c4d.ID_USERDATA,14])))\n    frequency=.45+2.2*rhythm\n    settle=min(12.0,max(.25,float(obj[c4d.ID_USERDATA,15])))\n    damping=min(2.0,max(.015,math.log(100.0)/(settle*2.0*math.pi*frequency)))\n    ripple=min(1.0,max(0.0,float(obj[c4d.ID_USERDATA,16])))\n    angle=min(30.0,max(0.0,float(obj[c4d.ID_USERDATA,17])))\n    duration=min(2.0,max(.05,float(obj[c4d.ID_USERDATA,18])))\n    anticipation=min(2.0,max(0.0,float(obj[c4d.ID_USERDATA,19])))\n    tilt_scale=min(HEIGHT*.20,RADIUS*math.tan(math.radians(angle)))/max(.001,HEIGHT*.16)\n    time=doc.GetTime().Get()\n    if enabled and gain>0:\n        states,forces,t0,dt=response(gain,frequency,damping,obj)\n        qx,qz,vx,vz=at_state(time,states,gain,frequency,damping,forces,t0,dt)\n        details,dgain,dfrequency,ddamping=detail_response(states,forces,dt,gain,frequency,damping)\n        rx,rz,rvx,rvz=at_state(time,details,dgain,dfrequency,ddamping,forces,t0,dt)\n        waves=wave_blend(time,states,forces,t0,dt,gain,duration,anticipation)\n        px,pz=-.9*waves*vx/(2.0*math.pi*frequency),-.9*waves*vz/(2.0*math.pi*frequency)\n        rpx,rpz=-.9*waves*rvx/(2.0*math.pi*dfrequency),-.9*waves*rvz/(2.0*math.pi*dfrequency)\n    else:\n        waves=0.0\n        qx=qz=px=pz=rx=rz=rpx=rpz=0.0\n    basis=spatial_basis()\n    raw=[]\n    peak=0.0\n    for b in basis:\n        bank_scale=waves+(1.0-waves)*tilt_scale\n        delta=bank_scale*(qx*b[0]+qz*b[2])+px*b[1]+pz*b[3]\n        delta+=ripple*waves*(rx*b[4]+rpx*b[5]+rz*b[6]+rpz*b[7])\n        raw.append(delta)\n        peak=max(peak,abs(delta))\n    # Limite automatico e suave, sem pedir ao usuario escala/calculos de estabilidade.\n    limit=HEIGHT*.20\n    factor=limit*math.tanh(peak/limit)/peak if peak>1e-12 else 1.0\n    points=[orient(x,y+(delta*factor+(sx*x+sz*z))*weight,z)\n            for (x,y,z,weight),delta in zip(REST,raw)]\n    obj.SetAllPoints(points)\n    obj.Message(c4d.MSG_UPDATE)\n\n\ndef continuous_main():\n    obj = op.GetObject()\n    if obj is None or not obj.CheckType(c4d.Opolygon): return\n    if obj.GetPointCount() != len(REST): return  # Nao editar a topologia.\n    enabled = obj[c4d.ID_USERDATA, 1]\n    level = bool(obj[c4d.ID_USERDATA,20])\n    sx,sz=world_slopes(obj,level)\n    amplitude = max(0.0, float(obj[c4d.ID_USERDATA, 2]))\n    speed = float(obj[c4d.ID_USERDATA, 3])\n    wavelength = max(0.001, float(obj[c4d.ID_USERDATA, 4]))\n    direction = float(obj[c4d.ID_USERDATA, 5])\n    ripple = min(1.0, max(0.0, float(obj[c4d.ID_USERDATA, 6])))\n    edge_lock = min(1.0, max(0.0, float(obj[c4d.ID_USERDATA, 7])))\n    phase = float(obj[c4d.ID_USERDATA, 8])\n    # Limite protege a altura das laterais contra inversao/interseccao.\n    amplitude = min(amplitude, HEIGHT * 0.20 / (1.0 + ripple))\n    if not enabled: amplitude = 0.0\n    time = doc.GetTime().Get()  # Segundos, inclusive subframes do render.\n    k = 2.0 * math.pi / wavelength\n    temporal = 2.0 * math.pi * speed * time\n    ca, sa = math.cos(direction), math.sin(direction)\n    points = []\n    for x, y, z, weight in REST:\n        u, v = x * ca + z * sa, -x * sa + z * ca\n        rho = min(1.0, math.hypot(x, z) / RADIUS)\n        # Suave no centro e na borda; 100% fixa a borda superior.\n        smooth = rho * rho * (3.0 - 2.0 * rho)\n        envelope = 1.0 - edge_lock * smooth\n        wave = math.sin(k * u - temporal + phase)\n        wave += ripple * math.sin(k * (1.7 * v + 0.4 * u)\n                                  - 1.3 * temporal + phase + 0.8)\n        points.append(orient(x, y + (amplitude * envelope * wave + (sx*x+sz*z)) * weight, z))\n    obj.SetAllPoints(points)\n    obj.Message(c4d.MSG_UPDATE)\n\ndef main():\n    obj=op.GetObject()\n    if obj is None:return\n    if int(obj[c4d.ID_USERDATA,21])==0:continuous_main()\n    else:reactive_main()\n'


def read_reference(tag):
    """Le apenas literais de tags nossas; nao executa codigo da cena."""
    code = tag[c4d.TPYTHON_CODE]
    values = {}
    for statement in ast.parse(code).body:
        if isinstance(statement, ast.Assign) and len(statement.targets)==1:
            target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id in ('REST','AXIS','HEIGHT','RADIUS'):
                values[target.id] = ast.literal_eval(statement.value)
    if set(values)!= {'REST','AXIS','HEIGHT','RADIUS'}:
        raise ValueError('Tag sem geometria de referencia reconhecida.')
    return values


def cube_geometry(size):
    nx=nz=32
    layers=16
    halfx,halfy,halfz=size.x*.5,size.y*.5,size.z*.5
    rest=[];faces=[]
    def grid(y,weight):
        start=len(rest)
        for j in range(nz+1):
            for i in range(nx+1):rest.append((-halfx+size.x*i/nx,y,-halfz+size.z*j/nz,weight))
        return [[start+j*(nx+1)+i for i in range(nx+1)] for j in range(nz+1)]
    top=grid(halfy,1.0);bottom=grid(-halfy,0.0)
    for j in range(nz):
        for i in range(nx):
            faces.append((top[j][i],top[j+1][i],top[j+1][i+1],top[j][i+1]))
            faces.append((bottom[j][i+1],bottom[j+1][i+1],bottom[j+1][i],bottom[j][i]))
    def boundary(g):
        return (g[0][:-1]+[g[j][nx] for j in range(nz)]+
                list(reversed(g[nz][1:]))+[g[j][0] for j in range(nz,0,-1)])
    upper=boundary(top);last=boundary(bottom)
    for layer in range(1,layers+1):
        t=1.0-layer/float(layers)
        if layer==layers:lower=last
        else:
            lower=[]
            for idx in boundary(top):
                x,y,z,w=rest[idx];lower.append(len(rest));rest.append((x,-halfy+size.y*t,z,t**4))
        for k in range(len(upper)):
            n=(k+1)%len(upper);faces.append((upper[k],upper[n],lower[n],lower[k]))
        upper=lower
    mesh=c4d.PolygonObject(len(rest),len(faces))
    mesh.SetAllPoints([c4d.Vector(x,y,z) for x,y,z,w in rest])
    for i,face in enumerate(faces):mesh.SetPolygon(i,c4d.CPolygon(*face))
    mesh.Message(c4d.MSG_UPDATE)
    return mesh,rest


def find_mesh(selected):
    """Aceita a malha atual ou seu cilindro original."""
    candidates = [selected]
    if selected.CheckType(c4d.Ocylinder) or selected.CheckType(c4d.Ocube):
        child = selected.GetDown()
        while child:
            candidates.append(child)
            child = child.GetNext()
    for obj in candidates:
        if not obj.CheckType(c4d.Opolygon): continue
        for tag in obj.GetTags():
            if (tag.CheckType(c4d.Tpython) and tag.GetName() in
                    ('Animacao - Liquido Fake','Reacao - Liquido Fake','Procedural - Liquido Fake','Liquido Facil','EasyLiquid')):
                return obj,tag
    return None,None


def code_for(rest,axis,height,radius):
    code = TAG_CODE
    for token,value in [('REST',rest),('AXIS',axis),('HEIGHT',height),('RADIUS',radius)]:
        code = code.replace('__'+token+'__',repr(value))
    compile(code,'Liquido Fake Procedural','exec')
    return code


def add_basic_controls(mesh,radius,height):
    control(mesh,'Ativar ondas',c4d.DTYPE_BOOL,True)
    control(mesh,'Amplitude das ondas',c4d.DTYPE_REAL,min(radius*.06,height*.08),c4d.DESC_UNIT_METER,0.0)
    control(mesh,'Velocidade da onda livre (ciclos/s)',c4d.DTYPE_REAL,.25)
    control(mesh,'Comprimento de onda',c4d.DTYPE_REAL,radius*2.5,c4d.DESC_UNIT_METER,.001)
    control(mesh,'Direcao da onda livre',c4d.DTYPE_REAL,0.0,c4d.DESC_UNIT_DEGREE)
    control(mesh,'Ondulacao secundaria',c4d.DTYPE_REAL,.45,c4d.DESC_UNIT_PERCENT,0.0,1.0)
    control(mesh,'Fixar borda',c4d.DTYPE_REAL,0.0,c4d.DESC_UNIT_PERCENT,0.0,1.0)
    control(mesh,'Fase da onda livre',c4d.DTYPE_REAL,0.0,c4d.DESC_UNIT_DEGREE)


def add_reactive_controls(mesh,height):
    for name,value,minimum,maximum in [
            ('Intensidade da reacao',1.0,0.0,20.0),
            ('Oscilacao (Hz)',1.2,.1,8.0),
            ('Amortecimento',.30,.03,2.0)]:
        # Constantes por tomada: historico recalculado com o valor atual.
        bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
        bc[c4d.DESC_NAME] = name
        bc[c4d.DESC_MIN],bc[c4d.DESC_MAX] = minimum,maximum
        bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
        desc = mesh.AddUserData(bc)
        mesh[desc] = value
    control(mesh,'Deslocamento maximo',c4d.DTYPE_REAL,height*.18,c4d.DESC_UNIT_METER,0.0,height*.20)


def simple_controls(mesh):
    existing={desc[1].id for desc,bc in mesh.GetUserDataContainer()}
    for desc,bc in mesh.GetUserDataContainer():
        ident=desc[1].id
        if ident<=12:
            bc[c4d.DESC_HIDE]=ident!=1
            if ident==1: bc[c4d.DESC_NAME]='Efeito ligado'
            mesh.SetUserDataContainer(desc,bc)
    if 13 not in existing:
        controls=[('Forca do movimento',.4,c4d.DESC_UNIT_PERCENT,0.0,2.0),
                  ('Ritmo das ondas',.30,c4d.DESC_UNIT_PERCENT,0.0,1.0),
                  ('Tempo para acomodar (segundos)',3.0,c4d.DESC_UNIT_REAL,.25,12.0),
                  ('Ondulacao',.65,c4d.DESC_UNIT_PERCENT,0.0,1.0)]
        for name,value,unit,minimum,maximum in controls:
            bc=c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
            bc[c4d.DESC_NAME]=name
            bc[c4d.DESC_UNIT]=unit
            bc[c4d.DESC_MIN],bc[c4d.DESC_MAX]=minimum,maximum
            bc[c4d.DESC_ANIMATE]=c4d.DESC_ANIMATE_OFF
            desc=mesh.AddUserData(bc)
            mesh[desc]=value
    for ident,name,value,minimum,maximum in [
            (17,'Inclinacao durante o movimento (graus)',10.0,0.0,30.0),
            (18,'Transicao para as ondas (segundos)',.35,.05,2.0),
            (19,'Antecipar transicao (segundos)',0.0,0.0,2.0)]:
        if ident not in existing:
            bc=c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
            bc[c4d.DESC_NAME]=name
            bc[c4d.DESC_UNIT]=c4d.DESC_UNIT_REAL
            if ident==19: bc[c4d.DESC_CUSTOMGUI]=c4d.CUSTOMGUI_REALSLIDER
            bc[c4d.DESC_MINSLIDER],bc[c4d.DESC_MAXSLIDER]=minimum,maximum
            bc[c4d.DESC_MIN],bc[c4d.DESC_MAX]=minimum,maximum
            bc[c4d.DESC_ANIMATE]=c4d.DESC_ANIMATE_OFF
            desc=mesh.AddUserData(bc)
            mesh[desc]=value
    if 20 not in existing:
        bc=c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
        bc[c4d.DESC_NAME]='Nivelar topo no mundo'
        bc[c4d.DESC_ANIMATE]=c4d.DESC_ANIMATE_OFF
        desc=mesh.AddUserData(bc)
        mesh[desc]=False
    if 21 not in existing:
        bc=c4d.GetCustomDataTypeDefault(c4d.DTYPE_LONG)
        bc[c4d.DESC_NAME]='Modo do liquido'
        bc[c4d.DESC_CUSTOMGUI]=c4d.CUSTOMGUI_CYCLE
        cycle=c4d.BaseContainer();cycle.SetString(0,'Ondas continuas');cycle.SetString(1,'Reagir ao movimento')
        bc[c4d.DESC_CYCLE]=cycle
        bc[c4d.DESC_ANIMATE]=c4d.DESC_ANIMATE_OFF
        desc=mesh.AddUserData(bc);mesh[desc]=1
    mesh.Message(c4d.MSG_UPDATE)


USER_DATA_NAMES={1:'Enabled',2:'Wave Amplitude',3:'Wave Speed (cycles/s)',4:'Wavelength',
5:'Wave Direction',6:'Secondary Ripples',7:'Edge Lock',8:'Wave Phase',9:'Responsiveness',
10:'Oscillation (Hz)',11:'Damping',12:'Maximum Displacement',13:'Motion Strength',
14:'Wave Rhythm',15:'Settling Time (s)',16:'Ripples',17:'Moving Tilt (deg)',
18:'Wave Transition (s)',19:'Transition Lead (s)',20:'Keep Surface Level in World Space',21:'Liquid Mode'}
def english_controls(mesh):
    for desc,bc in mesh.GetUserDataContainer():
        ident=desc[1].id
        if ident in USER_DATA_NAMES:
            bc[c4d.DESC_NAME]=USER_DATA_NAMES[ident]
            bc[c4d.DESC_SHORT_NAME]=USER_DATA_NAMES[ident]
            if ident==21:
                cycle=c4d.BaseContainer();cycle.SetString(0,'Continuous Waves');cycle.SetString(1,'Motion Response')
                bc[c4d.DESC_CYCLE]=cycle
            mesh.SetUserDataContainer(desc,bc)


def main():
    inherited_level=None
    selected = doc.GetActiveObject()
    if selected is None:
        c4d.gui.MessageDialog('Select a parametric cylinder, cube, or EasyLiquid mesh.')
        return
    try:
        mesh,tag = find_mesh(selected)
        updating = mesh is not None
        if updating:
            reference = read_reference(tag)
            rest,axis,height,radius = (reference[k] for k in ('REST','AXIS','HEIGHT','RADIUS'))
            if mesh.GetPointCount()!=len(rest):
                raise ValueError('Topology changed. Recreate the liquid from the original object.')
            # Le a posicao do proprio liquido: inclui seu pai e hierarquia.
            ids = {desc[1].id for desc,bc in mesh.GetUserDataContainer()}
            if ids not in (set(range(1,9)),set(range(1,10)),set(range(1,13)),set(range(1,17)),set(range(1,19)),set(range(1,20)),set(range(1,21)),set(range(1,22))):
                raise ValueError('User Data changed. Recreate the liquid to restore its controls.')
        else:
            if selected.CheckType(c4d.Ocube):
                size=selected[c4d.PRIM_CUBE_LEN]
                if min(size.x,size.y,size.z)<=0:raise ValueError('Dimensions must be positive.')
                height=size.y;radius=math.hypot(size.x,size.z)*.5;axis=c4d.PRIM_AXIS_YP
                mesh,rest=cube_geometry(size)
            elif selected.CheckType(c4d.Ocylinder):
                radius,height=float(selected[c4d.PRIM_CYLINDER_RADIUS]),float(selected[c4d.PRIM_CYLINDER_HEIGHT])
                axis=int(selected[c4d.PRIM_AXIS])
                if radius<=0 or height<=0:raise ValueError('Radius and height must be positive.')
                mesh,rest=geometry(radius,height,axis)
            else:raise ValueError('Select a parametric cylinder, cube, or EasyLiquid mesh.')
            mesh.SetName(selected.GetName()+' - EasyLiquid')
            add_basic_controls(mesh,radius,height)
            add_reactive_controls(mesh,height)
            tag = c4d.BaseTag(c4d.Tpython)
            tag[c4d.TPYTHON_FRAME] = True
            tag[c4d.TPYTHON_RESET] = False
            mesh.InsertTag(tag)
            phong = c4d.BaseTag(c4d.Tphong)
            phong[c4d.PHONGTAG_PHONG_ANGLELIMIT] = True
            phong[c4d.PHONGTAG_PHONG_ANGLE] = math.radians(60)
            mesh.InsertTag(phong)
            for st in selected.GetTags():
                if st.CheckType(c4d.Ttexture) and not st[c4d.TEXTURETAG_RESTRICTION]:
                    clone = st.GetClone(c4d.COPYFLAGS_0)
                    if clone is not None: mesh.InsertTag(clone)
        code = code_for(rest,axis,height,radius)
    except Exception as exc:
        traceback.print_exc()
        c4d.gui.MessageDialog('EasyLiquid '+VERSAO_SCRIPT+'\nUnable to prepare liquid:\n'+type(exc).__name__+': '+str(exc))
        return
    c4d.StopAllThreads()
    doc.StartUndo()
    try:
        if updating:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE,mesh)
            doc.AddUndo(c4d.UNDOTYPE_CHANGE,tag)
            old_code = tag[c4d.TPYTHON_CODE]
            if len(ids)==9:
                desc,bc=next((desc,bc) for desc,bc in mesh.GetUserDataContainer() if desc[1].id==9)
                if bc[c4d.DESC_NAME]!='Nivelar topo no mundo':
                    raise ValueError('Unrecognized control on the liquid mesh.')
                inherited_level=bool(mesh[desc])
                mesh.RemoveUserData(desc)
                data=mesh.GetDataInstance().GetContainerInstance(c4d.ID_USERDATA)
                if data is not None:data.RemoveData(9)
                add_reactive_controls(mesh,height)
            if len(ids)==12 and 'def detail_response(' not in old_code:
                if abs(float(mesh[c4d.ID_USERDATA,6])-.15)<1e-9:
                    mesh[c4d.ID_USERDATA,6]=.45
            if len(ids)==8:
                add_reactive_controls(mesh,height)
                mesh[c4d.ID_USERDATA,6]=.45
                # A onda perpetua da primeira versao impediria o repouso.
                mesh[c4d.ID_USERDATA,2] = 0.0
        else:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE,selected)
            doc.InsertObject(mesh,parent=selected)
            doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,mesh)
            selected[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.MODE_OFF
            selected[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = c4d.MODE_OFF
            selected.GetDataInstance().SetBool(MARCADOR,True)
            mesh[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.MODE_ON
            mesh[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = c4d.MODE_ON
        simple_controls(mesh)
        english_controls(mesh)
        if inherited_level is not None:mesh[c4d.ID_USERDATA,20]=inherited_level
        tag.SetName('EasyLiquid')
        tag[c4d.TPYTHON_FRAME] = True
        tag[c4d.TPYTHON_RESET] = False
        tag[c4d.TPYTHON_CODE] = code
        context = {'op':tag,'doc':doc,'__name__':'liquido_fake_tag'}
        exec(compile(code,'Liquido Fake - tag','exec'),context)
        context['main']()
        mesh.Message(c4d.MSG_UPDATE)
        tag.Message(c4d.MSG_UPDATE)
        doc.SetActiveObject(mesh)
    finally:
        doc.EndUndo()
    # Aquece o cache real da tag antes do primeiro Play.
    doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
    c4d.EventAdd()
    c4d.StatusSetText('EasyLiquid ready. Animate Position. Adjust settings in User Data.')



def run():
    """Entrada explicita do Script Manager; erros sempre chegam a um dialogo."""
    global doc
    try:
        doc = c4d.documents.GetActiveDocument()
        if doc is None:
            raise RuntimeError('No active document. Open a scene and select a cylinder or cube.')
        main()
    except Exception as exc:
        traceback.print_exc()
        c4d.gui.MessageDialog('EasyLiquid '+VERSAO_SCRIPT+'\nExecution error:\n'
                              +type(exc).__name__+': '+str(exc)
                              +'\nIf an object was partially created, undo before trying again.')


