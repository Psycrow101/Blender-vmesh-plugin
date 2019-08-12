from mathutils import *

from . import pyVRF

import importlib

import bpy
global bonesdata
bonesdata = []

#Import a model from a vmesh_c file
def import_file(context, filepath, *, add_hitboxes, global_matrix):
    importlib.reload(pyVRF)
    print('Reloading pyVRF...')

    #Get the data
    blocks = pyVRF.readBlocks( filepath )
    vbib = blocks['VBIB']

    #Go to object mode before doing anything
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    #Add geometry
    meshObject = addGeometry( vbib )

    #Add skeleton
    skeleton = addSkeleton(blocks['DATA'], meshObject, global_matrix)

    #Add hitboxes
    if add_hitboxes:
        addHitboxes( blocks['DATA'], skeleton )

    #add rigging
    addRig(meshObject, skeleton, vbib)

#Add geometry to the scene, returns the added object
def addGeometry( data ):
    # Create mesh and object
    me = bpy.data.meshes.new('Mesh')
    ob = bpy.data.objects.new('MeshObject', me)
    ob.location = (0,0,0)
    # Link object to scene
    view_layer = bpy.context.view_layer
    collection = view_layer.active_layer_collection.collection
    collection.objects.link(ob)
    view_layer.objects.active = ob
    view_layer.update()
 
    # Create mesh from given verts, edges, faces. Either edges or
    # faces should be [], or you ask for problems
    vertices = data["vertexdata"][0]["vertex"]
    indices = data["indexdata"][0]
    #print(indices)
    me.from_pydata(vertices, [], indices)

    # Add smooth for polygons
    for p in me.polygons:
        p.use_smooth = True
 
    # Update mesh with new data
    me.update(calc_edges=False)
    view_layer.update()
    #uv texcoords
    # me.uv_textures.new()
    uv_data = me.uv_layers.new().data
    for i in range(len(uv_data)):
        uv_data[i].uv = data["vertexdata"][0]["texcoords"][me.loops[i].vertex_index]
    view_layer.update()
    return ob

#Add a skeleton to the scene, returns the created skeleton
def addSkeleton( data, mesh, global_matrix):

    #Fetch scene
    view_layer = bpy.context.view_layer
    collection = view_layer.active_layer_collection.collection

    #Make armature
    armature = bpy.data.armatures.new('Armature')
    obj = bpy.data.objects.new('Armature', armature)

    # Set armature a parent for mesh
    mesh.parent = obj

    # Apply global matrix
    obj.matrix_world = global_matrix

    # Add X-ray for bones
    obj.show_in_front = True
    
    #Link the armature object in the scene and select it
    collection.objects.link(obj)
    view_layer.objects.active = obj
    obj.select_set(True)
    
    #Go to edit mode to access edit bones
    bpy.ops.object.mode_set(mode='EDIT')

    #Create skeleton bone by bone
    bones = {}
    for bone in data['m_skeleton']['m_bones']:
        #Add the new bone
        newBone = armature.edit_bones.new(name=bone['m_boneName'] )
        newBone.use_relative_parent = True

        #Set parent
        if len(bone['m_parentName']) > 0:
            newBone.parent = bones[bone['m_parentName']]
            newBone.use_connect = False

        #Set position
        m = bone['m_invBindPose']
        inverseBindPose = Matrix([[m[0],m[1],m[2],m[3]],
                                 [m[4],m[5],m[6],m[7]],
                                 [m[8],m[9],m[10],m[11]],
                                 [0, 0, 0, 1]])

        inverseBindPose.invert()

        #Set head and tail
        #newBone.head = inverseBindPose.to_translation()
        if newBone.parent:
            #Calculate the average position of siblings to set the parent tail to
            avgPos = Vector()
            num = 0
            for pc in newBone.parent.children:
                avgPos = avgPos + pc.head
                num = num + 1
            avgPos = avgPos / num
            #newBone.parent.tail = avgPos

        #Set tail radius - doesn't seem to do anything?
        newBone.tail_radius = bone['m_flSphereRadius']

        newBone.head = Vector((0,0,0))
        newBone.tail = Vector((5,0,0))
        newBone.matrix = inverseBindPose

        #Save the bone to parent later
        bones[bone['m_boneName']] = newBone

        #Add vertex group for the current bone
        mesh.vertex_groups.new(name=bone['m_boneName'])

        #global bonesdata array. Fix/Change?
        bonesdata.append(bone['m_boneName'])

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    return obj

#Add all hitboxes from the vmesh
def addHitboxes( data, skeleton ):

    hitboxes = data['m_hitboxsets']

    for group in hitboxes:
        groupname = group['key']
        for hitbox in group['value']['m_HitBoxes']:
            #Go to edit mode to add new bones
            bpy.ops.object.mode_set(mode='OBJECT')

            #Create new empty cube
            bpy.ops.object.add(type='EMPTY')
            empty = bpy.context.active_object
            empty.empty_display_type = 'CUBE'
            empty.name = groupname+"/"+hitbox['m_name']

            #Attach to its parent
            empty.parent = skeleton
            empty.parent_type = 'BONE'
            empty.parent_bone = hitbox['m_sBoneName']

            #Set size
            minBounds = Vector(hitbox['m_vMinBounds'])
            maxBounds = Vector(hitbox['m_vMaxBounds'])
            size = maxBounds - minBounds
            
            #Set the hitbox transform to its parent transform
            if empty.parent_bone in skeleton.data.bones:
                empty.matrix_local = skeleton.data.bones[empty.parent_bone].matrix_local            

            #Shift the hitbox since it is not centered around around the bone origin
            offset = maxBounds - size/2
            offset.rotate(empty.rotation_euler)
            empty.location += offset

            #Set the hitbox size
            empty.scale = size/2


    return True

#Add the armature modifier to the mesh
def addRig(mesh, skeleton, vbib):
    for index in range(len(vbib["vertexdata"][0]["blendindices"])):
        #print(index)
        if "blendweights" in vbib["vertexdata"][0]:
            weight = vbib["vertexdata"][0]["blendweights"][index]
            #print(index, weight)
            for q in range(len(weight)):
                vg = mesh.vertex_groups.get(bonesdata[vbib["vertexdata"][0]["blendindices"][index][q]])
                #not sure if this actually works correctly --v
                vg.add([index],  float( weight[q] ) /255.0, "REPLACE")

    mod = mesh.modifiers.new('Armature', 'ARMATURE')
    mod.object = skeleton
    mod.use_bone_envelopes = False
    mod.use_vertex_groups = True