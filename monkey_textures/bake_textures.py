import bpy, math, os
SP=os.path.dirname(os.path.abspath(__file__))+'/'
OUT=SP+'out/'
bpy.ops.wm.open_mainfile(filepath='/root/.claude/uploads/5dcfbe9b-14b2-5b5a-9b7c-0ba0ae0c1623/a3285ccf-Untitled.blend')
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for n in ('Untitled.001','Untitled.003'):
    im=bpy.data.images[n]; im.filepath=SP+n+'.png'; im.reload(); im.pack()
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'
sc.render.bake.margin=16

JOBS=[('Cube.003','Untitled.001',2048,'Monkey_Body'),('Cube.002','Untitled.002',1024,'Monkey_Hands')]


import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
def soften(o, imgname, sigma=1.6):
    im=bpy.data.images[imgname]; W,H=im.size
    a=np.empty(W*H*4,dtype=np.float32); im.pixels.foreach_get(a); a=a.reshape(H,W,4)
    uv=o.data.uv_layers['UVMap'].data
    m=Image.new('L',(W,H),0); d=ImageDraw.Draw(m)
    for poly in o.data.polygons:
        d.polygon([(uv[i].uv[0]*W, uv[i].uv[1]*H) for i in poly.loop_indices], fill=255, outline=255)
    mask=np.asarray(m)>0   # rows bottom-up like bpy pixels
    _,idx=ndimage.distance_transform_edt(~mask, return_indices=True)
    filled=a[idx[0],idx[1]]          # push island colors outward (no white bleed at seams)
    for c in range(3): filled[...,c]=ndimage.gaussian_filter(filled[...,c], sigma)
    filled[...,3]=1
    im.pixels.foreach_set(filled.ravel()); im.update()
    Image.fromarray((np.clip(filled[::-1,:,:3],0,1)*255).astype('uint8')).save(SP+imgname+'_soft.png')


import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
def soften(o, imgname, sigma=1.6):
    im=bpy.data.images[imgname]; W,H=im.size
    a=np.empty(W*H*4,dtype=np.float32); im.pixels.foreach_get(a); a=a.reshape(H,W,4)
    uv=o.data.uv_layers['UVMap'].data
    m=Image.new('L',(W,H),0); d=ImageDraw.Draw(m)
    for poly in o.data.polygons:
        d.polygon([(uv[i].uv[0]*W, uv[i].uv[1]*H) for i in poly.loop_indices], fill=255, outline=255)
    mask=np.asarray(m)>0
    _,idx=ndimage.distance_transform_edt(~mask, return_indices=True)
    f=a[idx[0],idx[1]].copy()
    for c in range(3): f[...,c]=ndimage.gaussian_filter(f[...,c], sigma)
    f[...,3]=1
    im.pixels.foreach_set(f.ravel()); im.update()

def unwrap(o):
    me=o.data
    old=me.uv_layers['UVMap']; old.name='UVMap_old'
    new=me.uv_layers.new(name='UVMap')
    me.uv_layers.active=new
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003, shape_method='CONCAVE', rotate_method='ANY')
    bpy.ops.object.mode_set(mode='OBJECT')

def build_bake_mat(o, oldimg, target):
    mat=o.material_slots[0].material
    orig=mat.node_tree.copy()  # keep for restore
    nt=mat.node_tree; N=nt.nodes; L=nt.links
    for n in list(N): N.remove(n)
    def node(t,**kw):
        n=N.new(t)
        for k,v in kw.items(): setattr(n,k,v)
        return n
    uvo=node('ShaderNodeUVMap'); uvo.uv_map='UVMap_old'
    tex=node('ShaderNodeTexImage'); tex.image=bpy.data.images[oldimg]; tex.interpolation='Cubic'; tex.extension='EXTEND'
    L.new(uvo.outputs['UV'],tex.inputs['Vector'])
    tc=node('ShaderNodeTexCoord')
    # luminance -> mask (1 = skin/gray, 0 = fur/white)
    rgb2bw=node('ShaderNodeRGBToBW'); L.new(tex.outputs['Color'],rgb2bw.inputs[0])
    # fuzzy edge noise (3D, seamless)
    nz_edge=node('ShaderNodeTexNoise'); nz_edge.inputs['Scale'].default_value=180; nz_edge.inputs['Detail'].default_value=6
    L.new(tc.outputs['Object'],nz_edge.inputs['Vector'])
    add=node('ShaderNodeMath',operation='MULTIPLY_ADD')
    L.new(nz_edge.outputs['Fac'],add.inputs[0]); add.inputs[1].default_value=0.22
    L.new(rgb2bw.outputs[0],add.inputs[2])  # lum + noise*0.16
    mask=node('ShaderNodeMapRange'); mask.clamp=True
    L.new(add.outputs[0],mask.inputs['Value'])
    mask.inputs['From Min'].default_value=0.66; mask.inputs['From Max'].default_value=0.92; mask.interpolation_type='SMOOTHERSTEP'
    mask.inputs['To Min'].default_value=1.0; mask.inputs['To Max'].default_value=0.0
    # fur: directional strands (along Z on torso/head, along Y on arms) + clumps
    sep=node('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'],sep.inputs[0])
    absy=node('ShaderNodeMath',operation='ABSOLUTE'); L.new(sep.outputs['Y'],absy.inputs[0])
    armw=node('ShaderNodeMapRange'); armw.clamp=True; L.new(absy.outputs[0],armw.inputs['Value'])
    armw.inputs['From Min'].default_value=0.45; armw.inputs['From Max'].default_value=0.75
    def strands(stretch):
        mp=node('ShaderNodeMapping'); mp.inputs['Scale'].default_value=stretch
        L.new(tc.outputs['Object'],mp.inputs['Vector'])
        warp=node('ShaderNodeTexNoise'); warp.inputs['Scale'].default_value=6
        L.new(tc.outputs['Object'],warp.inputs['Vector'])
        vm=node('ShaderNodeVectorMath',operation='MULTIPLY_ADD'); L.new(warp.outputs['Color'],vm.inputs[0])
        vm.inputs[1].default_value=(0.6,0.6,0.6); L.new(mp.outputs[0],vm.inputs[2])
        n=node('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=1.0; n.inputs['Detail'].default_value=3; n.inputs['Roughness'].default_value=0.6
        L.new(vm.outputs[0],n.inputs['Vector']); return n
    sz=strands((110,110,6)); sy=strands((110,6,110))
    smix=node('ShaderNodeMix'); smix.data_type='FLOAT'
    L.new(armw.outputs['Result'],smix.inputs['Factor']); L.new(sz.outputs['Fac'],smix.inputs[2]); L.new(sy.outputs['Fac'],smix.inputs[3])
    clump=node('ShaderNodeTexVoronoi'); clump.feature='SMOOTH_F1'; clump.inputs['Scale'].default_value=60; clump.inputs['Smoothness'].default_value=0.6
    L.new(tc.outputs['Object'],clump.inputs['Vector'])
    mott=node('ShaderNodeTexNoise'); mott.inputs['Scale'].default_value=8; mott.inputs['Detail'].default_value=3
    L.new(tc.outputs['Object'],mott.inputs['Vector'])
    f1=node('ShaderNodeMath',operation='MULTIPLY'); L.new(smix.outputs[0],f1.inputs[0]); f1.inputs[1].default_value=0.8
    f2=node('ShaderNodeMath',operation='MULTIPLY_ADD'); L.new(clump.outputs['Distance'],f2.inputs[0]); f2.inputs[1].default_value=-0.35; L.new(f1.outputs[0],f2.inputs[2])
    f3=node('ShaderNodeMath',operation='MULTIPLY_ADD'); L.new(mott.outputs['Fac'],f3.inputs[0]); f3.inputs[1].default_value=0.2; L.new(f2.outputs[0],f3.inputs[2])
    furramp=node('ShaderNodeValToRGB'); cr=furramp.color_ramp
    cr.elements[0].position=0.15; cr.elements[0].color=(0.68,0.67,0.66,1)
    e=cr.elements.new(0.38); e.color=(0.88,0.875,0.86,1)
    cr.elements[-1].position=0.58; cr.elements[-1].color=(0.98,0.975,0.965,1)
    L.new(f3.outputs[0],furramp.inputs['Fac'])
    # skin: gray with soft mottling + fine pores
    snz=node('ShaderNodeTexNoise'); snz.inputs['Scale'].default_value=25; snz.inputs['Detail'].default_value=6
    L.new(tc.outputs['Object'],snz.inputs['Vector'])
    pore=node('ShaderNodeTexNoise'); pore.inputs['Scale'].default_value=600
    L.new(tc.outputs['Object'],pore.inputs['Vector'])
    sm=node('ShaderNodeMath',operation='MULTIPLY_ADD'); L.new(pore.outputs['Fac'],sm.inputs[0]); sm.inputs[1].default_value=0.12
    L.new(snz.outputs['Fac'],sm.inputs[2])
    skinramp=node('ShaderNodeValToRGB'); sr=skinramp.color_ramp
    sr.elements[0].position=0.40; sr.elements[0].color=(0.34,0.33,0.33,1)
    sr.elements[1].position=0.85;  sr.elements[1].color=(0.44,0.43,0.425,1)
    L.new(sm.outputs[0],skinramp.inputs['Fac'])
    mix=node('ShaderNodeMix'); mix.data_type='RGBA'
    L.new(mask.outputs['Result'],mix.inputs['Factor'])
    L.new(furramp.outputs['Color'],mix.inputs[6]); L.new(skinramp.outputs['Color'],mix.inputs[7])
    em=node('ShaderNodeEmission'); L.new(mix.outputs[2],em.inputs['Color'])
    out=node('ShaderNodeOutputMaterial'); L.new(em.outputs[0],out.inputs['Surface'])
    tgt=node('ShaderNodeTexImage'); tgt.image=target; N.active=tgt; tgt.select=True
    return mat, orig

def bake(o, typ, img, samples):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    sc.cycles.samples=samples
    bpy.ops.object.bake(type=typ, use_clear=True, margin=16)
    print('baked',o.name,typ)

for obn,oldimg,res,name in JOBS:
    o=bpy.data.objects[obn]
    soften(o,oldimg)
    unwrap(o)
    col=bpy.data.images.new(name+'_Color',res,res); col.colorspace_settings.name='sRGB'
    ao=bpy.data.images.new(name+'_AO',res,res,float_buffer=False); ao.colorspace_settings.name='Non-Color'
    mat,orig=build_bake_mat(o,oldimg,col)
    bake(o,'EMIT',col,8)
    mat.node_tree.nodes.active.image=ao
    sc.world.light_settings.distance=0.15 if sc.world else None
    bake(o,'AO',ao,96)
    col.filepath_raw=OUT+name+'_Color_raw.png'; col.file_format='PNG'; col.save()
    ao.filepath_raw=OUT+name+'_AO.png'; ao.file_format='PNG'; ao.save()
    o.data.uv_layers.remove(o.data.uv_layers['UVMap_old'])
    o.data.uv_layers['UVMap'].active_render=True
    # simple final material: image -> base color
    nt=mat.node_tree; N=nt.nodes
    for n in list(N): N.remove(n)
    t=N.new('ShaderNodeTexImage'); b=N.new('ShaderNodeBsdfPrincipled'); out=N.new('ShaderNodeOutputMaterial')
    b.inputs['Roughness'].default_value=0.9
    nt.links.new(t.outputs['Color'],b.inputs['Base Color']); nt.links.new(b.outputs[0],out.inputs[0])
    t.name='FINAL_TEX'; t.label=name
    print('done',obn)
bpy.ops.wm.save_as_mainfile(filepath=OUT+'stage1.blend')
