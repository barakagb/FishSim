# ##### BEGIN GPL LICENSE BLOCK #####
#
#  fishsim.py  -- a script to apply a fish swimming simulation to an armature
#  by Ian Huish (nerk)
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
bl_info = {
    "name": "FishSim",
    "author": "Ian Huish (nerk)",
    "version": (0, 1, 0),
    "blender": (2, 78, 0),
    "location": "Toolshelf>Tools Tab>FishSim",
    "description": "Apply fish swimming action to a Rigify Shark armature",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Animation"}

import bpy
import mathutils,  math, os
from bpy.props import FloatProperty, IntProperty, BoolProperty, EnumProperty, StringProperty
from random import random

def add_preset_files():
    presets   = bpy.utils.user_resource('SCRIPTS', "presets")
    mypresets = os.path.join(presets, "operator\\armature.fsim_run")
    if not os.path.exists(mypresets):
        os.makedirs(mypresets)    
        print("Presets dir added:", mypresets)
    mypath = os.path.join(mypresets, "myfile.xxx")

    # fout     = open(mypath)
    

def updateStartFrame(self, context):
    start = context.scene.fsim_start_frame
    end = context.scene.fsim_end_frame
    if start >= end:
        start = end

def updateEndFrame(self, context):
    start = context.scene.fsim_start_frame
    end = context.scene.fsim_end_frame
    if end <= start:
        end = start

bpy.types.Scene.fsim_start_frame = IntProperty(name="Simulation Start Frame", default=1, update=updateStartFrame)  
bpy.types.Scene.fsim_end_frame = IntProperty(name="Simulation End Frame", default=250, update=updateEndFrame)  


class ARMATURE_OT_FSim_Add(bpy.types.Operator):
    """Add a target object for the simulated fish to follow"""
    bl_label = "Add a target"
    bl_idname = "armature.fsim_add"
    bl_options = {'REGISTER', 'UNDO'}
    


    def execute(self, context):
        #Get the object
        TargetRig = context.object
        if TargetRig.type != "ARMATURE":
            print("Not an Armature", context.object.type)
            return {'CANCELLED'}
       
        TargetRoot = TargetRig.pose.bones.get("root")
        if (TargetRoot is None):
            print("No root bone in Armature")
            return {'CANCELLED'}

        TargetRoot["TargetProxy"] = TargetRig.name + '_proxy'
            
        #Add the proxy object
        bpy.ops.mesh.primitive_cube_add()
        bound_box = bpy.context.active_object
        #copy transforms
        bound_box.dimensions = TargetRig.dimensions
        bound_box.location = TargetRig.location
        bound_box.rotation_euler = TargetRig.rotation_euler
        bound_box.name = TargetRoot["TargetProxy"]
        bound_box.draw_type = 'WIRE'
        bound_box["FSim"] = "FSim_"+TargetRig.name[:3]
        if "FSim" in bound_box:
            print("FSim Found")
        bound_box.select = False
        #context.active_pose_bone = TargetRoot
        
        return {'FINISHED'}

class ARMATURE_OT_FSim_Run(bpy.types.Operator):
    """Simulate and add keyframes for the armature to make it swim towards the target"""
    bl_label = "Simulate"
    bl_idname = "armature.fsim_run"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}
    
    add_preset_files()

    
    #State Variables
    sVelocity = FloatProperty(name="Velocity", description="Speed", default=0.0, min=0)
    sEffort = FloatProperty(name="Effort", description="The effort going into swimming", default=1.0, min=0)
    sTurn = FloatProperty(name="Turn", description="The intent to go left of right (positive is right)", default=0.0)
    sRise = FloatProperty(name="Rise", description="The intent to go up or down (positive is up", default=0.0)
    sFreq = FloatProperty(name="Frequency", description="Current frequency of tail movement in frames per cycle", default=0.0)
    sTailAngle = FloatProperty(name="Tail Angle", description="Current max tail angle in degrees", default=0.0)
    sTailAngleOffset = FloatProperty(name="Tail Angle Offset", description="Offset angle for turning in degrees", default=0.0)

    #Property declaration
    pMass = FloatProperty(name="Mass", description="Total Mass", default=30.0, min=0, max=3000.0)
    pDrag = FloatProperty(name="Drag", description="Total Drag", default=8.0, min=0, max=3000.0)
    pPower = FloatProperty(name="Power", description="Forward force for given tail fin speed and angle", default=20.0, min=0)
    pMaxFreq = FloatProperty(name="Maximum frequency", description="Maximum frequence of tail movement in frames per cycle", default=30.0)
    pEffortGain = FloatProperty(name="Effort Gain", description="The amount of effort required for a given distance to target", default=0.5, min=0.0)
    pEffortRamp = FloatProperty(name="Effort Ramp", description="First Order factor for ramping up effort", default=0.2, min=0.0, max=0.6)
    pAngularDrag = FloatProperty(name="AngularDrag", description="Resistance to changing direction", default=1.0, min=0)
    pTurnAssist = FloatProperty(name="TurnAssist", description="Fake Turning effect (0 - 10)", default=3.0, min=0)
    pMaxTailAngle = FloatProperty(name="Max Tail Angle", description="Max tail angle", default=15.0, min=0, max=30.0)
    pMaxSteeringAngle = FloatProperty(name="Max Steering Angle", description="Max steering tail angle", default=15.0, min=0, max=40.0)
    pMaxVerticalAngle = FloatProperty(name="Max vertical Angle", description="Max steering angle for vertical", default=0.1, min=0, max=40.0)
    pMaxTailFinAngle = FloatProperty(name="Max Tail Fin Angle", description="Max tail fin angle", default=15.0, min=0, max=30.0)
    pTailFinGain = FloatProperty(name="Tail Fin Gain", description="Tail Fin speed of response to movement", default=5.0, min=0, max=25.0)
    pTailFinStiffness = FloatProperty(name="Tail Fin Stiffness", description="Tail Fin Stiffness", default=0.2, min=0, max=1.0)
    pTailFinStubRatio = FloatProperty(name="Tail Fin Stub Ratio", description="Ratio for the bottom part of the tail", default=0.3, min=0, max=3.0)
    pMaxSideFinAngle = FloatProperty(name="Max Side Fin Angle", description="Max side fin angle", default=15.0, min=0, max=60.0)
    pSideFinGain = FloatProperty(name="Side Fin Gain", description="Side Fin speed of response to movement", default=2.0, min=0, max=100.0)
    pSideFinStiffness = FloatProperty(name="Side Fin Stiffness", description="Side Fin Stiffness", default=0.2, min=0, max=10.0)
    pChestRatio = FloatProperty(name="Chest Ratio", description="Ratio of the front of the fish to the rear", default=0.5, min=0, max=2.0)
    pChestRaise = FloatProperty(name="Chest Raise Factor", description="Chest raises during turning", default=1.0, min=0, max=20.0)
    pLeanIntoTurn = FloatProperty(name="LeanIntoTurn", description="Amount it leans into the turns", default=1.0, min=0, max=20.0)
    pRandom = FloatProperty(name="Random", description="Random amount", default=0.25, min=0, max=1.0)

    def RemoveKeyframes(self, armature, bones):
        dispose_paths = []
        #dispose_paths.append('pose.bones["{}"].rotation_quaternion'.format(bone.name))
        for fcurve in armature.animation_data.action.fcurves:
            if (fcurve.data_path == "location" or fcurve.data_path == "rotation_euler"):
                armature.animation_data.action.fcurves.remove(fcurve)
        for bone in bones:
            #bone.rotation_mode='XYZ'
            #dispose_paths.append('pose.bones["{}"].rotation_euler'.format(bone.name))
            dispose_paths.append('pose.bones["{}"].rotation_quaternion'.format(bone.name))
            dispose_paths.append('pose.bones["{}"].scale'.format(bone.name))
        dispose_curves = [fcurve for fcurve in armature.animation_data.action.fcurves if fcurve.data_path in dispose_paths]
        for fcurve in dispose_curves:
            armature.animation_data.action.fcurves.remove(fcurve)
        
    def draw(self, context):
        layout = self.layout
        layout.operator('screen.repeat_last', text="Repeat", icon='FILE_REFRESH' )
        
        box = layout.box()
        box.label("Main Parameters")
        box.prop(self, "pMass")
        box.prop(self, "pDrag")
        box.prop(self, "pPower")
        box.prop(self, "pMaxFreq")
        box.prop(self, "pMaxTailAngle")
        box = layout.box()
        box.label("Turning Parameters")
        box.prop(self, "pAngularDrag")
        box.prop(self, "pMaxSteeringAngle")
        box.prop(self, "pTurnAssist")
        box.prop(self, "pLeanIntoTurn")
        box = layout.box()
        box.label("Fine Tuning")
        box.prop(self, "pEffortGain")
        box.prop(self, "pEffortRamp")
        box.prop(self, "pMaxTailFinAngle")
        box.prop(self, "pTailFinGain")
        box.prop(self, "pTailFinStiffness")
        box.prop(self, "pTailFinStubRatio")
        box.prop(self, "pMaxSideFinAngle")
        box.prop(self, "pSideFinGain")
        box.prop(self, "pSideFinStiffness")
        box.prop(self, "pChestRatio")
        box.prop(self, "pChestRaise")
        box.prop(self, "pMaxVerticalAngle")
        box.prop(self, "pRandom")
        
    #Set Effort and Direction properties to try and reach the target.
    def Target(self, TargetRig, TargetProxy):
        RigDirn = mathutils.Vector((0,-1,0)) * TargetRig.matrix_world.inverted()
        #print("RigDirn: ", RigDirn)
        
        #distance to target
        if TargetProxy != None:
            TargetDirn = (TargetProxy.matrix_world.to_translation() - TargetRig.location)
        else:
            TargetDirn = mathutils.Vector((0,-10,0))
        DifDot = TargetDirn.dot(RigDirn)
        
        #horizontal angle to target - limit max turning effort at 90 deg
        RigDirn2D = mathutils.Vector((RigDirn.x, RigDirn.y))
        TargetDirn2D = mathutils.Vector((TargetDirn.x, TargetDirn.y))
        AngleToTarget = math.degrees(RigDirn2D.angle_signed(TargetDirn2D, math.radians(180)))
        DirectionEffort = AngleToTarget/90.0
        DirectionEffort = min(1.0,DirectionEffort)
        DirectionEffort = max(-1.0,DirectionEffort)
        
        #vertical angle to target - limit max turning effort at 20 deg
        RigDirn2DV = mathutils.Vector(((RigDirn.y**2 + RigDirn.x**2)**0.5, RigDirn.z))
        TargetDirn2DV = mathutils.Vector(((TargetDirn.y**2 + TargetDirn.x**2)**0.5, TargetDirn.z))
        AngleToTargetV = math.degrees(RigDirn2DV.angle_signed(TargetDirn2DV, math.radians(180)))
        DirectionEffortV = AngleToTargetV/20.0
        DirectionEffortV = min(1.0,DirectionEffortV)
        DirectionEffortV = max(-1.0,DirectionEffortV)
        
        #Return normalised required effort, turning factor, and ascending factor
        return DifDot,DirectionEffort,DirectionEffortV
        
    #Handle the object movement
    def ObjectMovment(self, TargetRig, ForwardForce, AngularForce, AngularForceV, nFrame, TargetProxy):
        RigDirn = mathutils.Vector((0,-1,0)) * TargetRig.matrix_world.inverted()
        #Total force is tail force - drag
        DragForce = self.pDrag * self.sVelocity ** 2.0
        self.sVelocity += (ForwardForce - DragForce) / self.pMass
        #print("Fwd, Drag: ", ForwardForce, DragForce)
        TargetRig.location += self.sVelocity * RigDirn
        TargetRig.keyframe_insert(data_path='location',  frame=(nFrame))
        
        #Let's be simplistic - just rotate object based on angluar force
        TargetRig.rotation_euler.z += math.radians(AngularForce)
        TargetRig.rotation_euler.x += math.radians(AngularForceV)
        TargetRig.keyframe_insert(data_path='rotation_euler',  frame=(nFrame))
        
        
        
#Handle the movement of the bones within the armature        
    def BoneMovement(self, TargetRig, startFrame, endFrame, scene):
    
        #Check the required Rigify bones are present
        root = TargetRig.pose.bones.get("root")
        torso = TargetRig.pose.bones.get("torso")
        spine_master = TargetRig.pose.bones.get("spine_master")
        back_fin1 = TargetRig.pose.bones.get("back_fin_masterBk.001")
        back_fin2 = TargetRig.pose.bones.get("back_fin_masterBk")
        back_fin_middle = TargetRig.pose.bones.get("DEF-back_fin.T.001.Bk")
        chest = TargetRig.pose.bones.get("chest")
        SideFinL = TargetRig.pose.bones.get("side_fin.L")
        SideFinR = TargetRig.pose.bones.get("side_fin.R")
        if (spine_master is None) or (torso is None) or (chest is None) or (back_fin1 is None) or (back_fin2 is None) or (back_fin_middle is None) or (SideFinL is None) or (SideFinR is None):
            print("Not an Suitable Rigify Armature", context.object.type)
            return 0,0
            
        #initialise state variabiles
        sState = 0.0
        AngularForceV = 0.0
            
        #Get TargetProxy object details
        try:
            TargetProxyName = root["TargetProxy"]
            TargetProxy = bpy.data.objects[TargetProxyName]
        except:
            TargetProxy = None

        #Go back to the start before removing keyframes to remember starting point
        scene.frame_set(startFrame)
       
        #Delete existing keyframes
        try:
            self.RemoveKeyframes(TargetRig, [spine_master, back_fin1, back_fin2, chest, SideFinL, SideFinR])
        except:
            print("info: no keyframes")
        
        #record to previous tail position
        scene.frame_set(startFrame)
        
        #randomise parameters
        rFact = self.pRandom
        rMaxTailAngle = self.pMaxTailAngle * (1 + (random() * 2.0 - 1.0) * rFact)
        rMaxFreq = self.pMaxFreq * (1 + (random() * 2.0 - 1.0) * rFact)

        #simulate for each frame
        for nFrame in range(startFrame, endFrame):
            scene.frame_set(nFrame)
            
            #Get the effort and direction change to head toward the target
            RqdEffort, RqdDirection, RqdDirectionV = self.Target(TargetRig, TargetProxy)
            self.sEffort = self.pEffortGain * RqdEffort * self.pEffortRamp + self.sEffort * (1.0-self.pEffortRamp)
            self.sEffort = min(self.sEffort, 1.0)
            #print("Required, Effort:", RqdEffort, self.sEffort)
            
            #Convert effort into tail frequency and amplitude
            self.sFreq = rMaxFreq * (1.0/(self.sEffort+ 0.01))
            self.sTailAngle = rMaxTailAngle * self.sEffort
            
            #Convert direction into Tail angle
            self.sTailAngleOffset = self.sTailAngleOffset * (1 - self.pEffortRamp) + RqdDirection * self.pMaxSteeringAngle * self.pEffortRamp
            #print("TailOffset: ", self.sTailAngleOffset)
            
            
            #Spine Movement
            sState = sState + 360.0 / self.sFreq
            xTailAngle = math.sin(math.radians(sState))*math.radians(rMaxTailAngle) + math.radians(self.sTailAngleOffset)
            #print("TailAngle", xTailAngle)
            spine_master.rotation_quaternion = mathutils.Quaternion((0.0, 0.0, 1.0), xTailAngle)
            spine_master.keyframe_insert(data_path='rotation_quaternion',  frame=(nFrame))
            ChestRot = mathutils.Quaternion((0.0, 0.0, 1.0), -xTailAngle * self.pChestRatio - math.radians(self.sTailAngleOffset))
            chest.rotation_quaternion = ChestRot * mathutils.Quaternion((1.0, 0.0, 0.0), -math.fabs(math.radians(self.sTailAngleOffset))*self.pChestRaise)
            #print("Torso:", self.sTailAngleOffset)
            torso.rotation_quaternion = mathutils.Quaternion((0.0, 1.0, 0.0), -math.radians(self.sTailAngleOffset)*self.pLeanIntoTurn
)
            chest.keyframe_insert(data_path='rotation_quaternion',  frame=(nFrame))
            torso.keyframe_insert(data_path='rotation_quaternion',  frame=(nFrame))
            scene.update()

            
            #Tail Movment
            if (nFrame == startFrame):
                back_fin_dif = 0
            else:
                back_fin_dif = (back_fin_middle.matrix.decompose()[0].x - old_back_fin.x)
            #print("back_fin dif: ", nFrame, back_fin_dif)
            #print("new_back_fin", nFrame, back_fin_middle.matrix.decompose()[0])
            old_back_fin = back_fin_middle.matrix.decompose()[0]
            
            #Tail Fin angle based on Tail movement
            pMaxTailScale = self.pMaxTailFinAngle * 0.4 / 30.0
            currentTailScale = back_fin1.scale[1]
            if (back_fin_dif < 0) :
                TailScaleIncr = (1 + pMaxTailScale - currentTailScale) * self.pTailFinGain * math.fabs(back_fin_dif)
                #print("Positive scale: ", TailScaleIncr)
            else:
                TailScaleIncr = (1 - pMaxTailScale - currentTailScale) * self.pTailFinGain * math.fabs(back_fin_dif)
                #print("Negative scale: ", TailScaleIncr)
            
            #Tail Fin stiffness factor
            TailFinStiffnessIncr = (1 - currentTailScale) * self.pTailFinStiffness
            
            if (nFrame == startFrame):
                back_fin1_scale = 1.0
            else:
                back_fin1_scale = back_fin1.scale[1] + TailScaleIncr + TailFinStiffnessIncr
                
            #Limit Tail Fin maximum deflection    
            if (back_fin1_scale > (pMaxTailScale + 1)):
                back_fin1_scale = pMaxTailScale + 1
            if (back_fin1_scale < (-pMaxTailScale + 1)):
                back_fin1_scale = -pMaxTailScale + 1
            back_fin1.scale[1] = back_fin1_scale
            back_fin2.scale[1] = 1 - (1 - back_fin1_scale) * self.pTailFinStubRatio
            scene.update()
            #print("New Scale:", back_fin1.scale[1])
            back_fin1.keyframe_insert(data_path='scale',  frame=(nFrame))
            back_fin2.keyframe_insert(data_path='scale',  frame=(nFrame))
            
            #Side Fin angle based on Tail movement
            pMaxSideFinAngle = self.pMaxSideFinAngle
            currentSideFinRot = math.degrees(SideFinL.rotation_quaternion.to_euler().x)
            if (back_fin_dif < 0) :
                SideIncr = (pMaxSideFinAngle - currentSideFinRot) * self.pSideFinGain * math.fabs(back_fin_dif)
                #print("Side Positive scale: ", SideIncr)
            else:
                SideIncr = (-pMaxSideFinAngle - currentSideFinRot) * self.pSideFinGain * math.fabs(back_fin_dif)
                #print("Side Negative scale: ", SideIncr)
            
            #Side Fin stiffness factor
            SideFinStiffnessIncr = -currentSideFinRot * self.pSideFinStiffness
            
            if (nFrame == startFrame):
                SideFinRot = 0.0
            else:
                SideFinRot = currentSideFinRot + SideIncr + SideFinStiffnessIncr
                #print("Current, incr, stiff: ", currentSideFinRot, SideIncr, SideFinStiffnessIncr)

            #Limit Side Fin maximum deflection    
            if (SideFinRot > pMaxSideFinAngle):
                SideFinRot = pMaxSideFinAngle
            if (SideFinRot < -pMaxSideFinAngle):
                SideFinRot = -pMaxSideFinAngle
            SideFinL.rotation_quaternion = mathutils.Quaternion((1,0,0), math.radians(-SideFinRot))
            SideFinR.rotation_quaternion = mathutils.Quaternion((1,0,0), math.radians(SideFinRot))
            scene.update()
            SideFinL.keyframe_insert(data_path='rotation_quaternion',  frame=(nFrame))
            SideFinR.keyframe_insert(data_path='rotation_quaternion',  frame=(nFrame))
            
            #Do Object movment with Forward force and Angular force
            TailFinAngle = (back_fin1_scale - 1.0) * 30.0 / 0.4
            TailFinAngleForce = math.sin(math.radians(TailFinAngle))
            ForwardForce = -back_fin_dif * TailFinAngleForce * self.pPower
            
            #Angular force due to 'swish'
            AngularForce = back_fin_dif  / self.pAngularDrag
            
            #Angular force due to rudder effect
            AngularForce += -xTailAngle * self.sVelocity / self.pAngularDrag
            
            #Fake Angular force to make turning more effective
            AngularForce += -(self.sTailAngleOffset/self.pMaxSteeringAngle) * self.pTurnAssist
            
            #Angular force for vertical movement
            AngularForceV = AngularForceV * (1 - self.pEffortRamp) + RqdDirectionV * self.pMaxVerticalAngle
            
            
            #print("TailFinAngle, AngularForce", xTailAngle, AngularForce)
            self.ObjectMovment(TargetRig, ForwardForce, AngularForce, AngularForceV, nFrame, TargetProxy)

        
    def execute(self, context):
        #Get the object
        TargetRig = context.object
        scene = context.scene
        if TargetRig.type != "ARMATURE":
            print("Not an Armature", context.object.type)
            return  {'FINISHED'}
       
        self.BoneMovement(TargetRig, scene.fsim_start_frame, scene.fsim_end_frame, scene)   
        
        return {'FINISHED'}


#Populate operator
#Search the scene for existing targets (for example from Crowd Master), duplicate the
#selected armature and skin, locate at the targets and run simulation        
class ARMATURE_OT_FSim_Populate(bpy.types.Operator):
    """Add a copy of this character to every marked target and run the simulation"""
    bl_label = "Simulate All"
    bl_idname = "armature.fsim_populate"
    bl_options = {'REGISTER', 'UNDO'}
    
    pStartAngle = FloatProperty(name="StartAngle", description="Starting angle compared to target object in degrees", default=0.0)

    def draw(self, context):
        layout = self.layout
        layout.operator('screen.repeat_last', text="Repeat", icon='FILE_REFRESH' )
        
        layout.prop(self, "pStartAngle")

    def execute(self, context):
        print("Populate")
        
        scene = context.scene
        src_obj = context.object
        if src_obj.type != 'ARMATURE':
            return {'CANCELLED'}
        
        #make a list of armatures
        armatures = {}
        for obj in scene.objects:
            if obj.type == "ARMATURE":
                root = obj.pose.bones.get("root")
                if root != None:
                    if 'TargetProxy' in root:
                        proxyName = root['TargetProxy']
                        if len(proxyName) > 1:
                            armatures[proxyName] = obj.name
        #make a list of objects with armature modifiers pointing to the list of armatures
        
        #make a list of objects parented to the armature
        
        #for each target...
        for obj in scene.objects:
            if "FSim" in obj:
                #Animate the fish, duplicating if required
                scene.frame_set(scene.fsim_start_frame)
                scene.update()
                
                #if a rig hasn't already been paired with this target, and it's the right target type for this rig, then add a duplicated rig at this location
                if (obj.name not in armatures) and (obj["FSim"][-3:] == src_obj.name[:3]):
                    print("time to duplicate")

                    #If there is not already a matching armature, duplicate the template and update the link field
                    new_obj = src_obj.copy()
                    new_obj.data = src_obj.data.copy()
                    new_obj.animation_data_clear()
                    scene.objects.link(new_obj)
                    new_obj.location = obj.location
                    new_obj.rotation_euler = obj.rotation_euler
                    new_root = new_obj.pose.bones.get('root')
                    new_root['TargetProxy'] = obj.name
                    scene.objects.active = new_obj
                    bpy.ops.armature.fsim_run()
                    
                    #then duplicate the dependents and re-link
                    for childObj in src_obj.children:
                        print("Copying child: ", childObj.name)
                        new_child = childObj.copy()
                        new_child.data = childObj.data.copy()
                        new_child.animation_data_clear()
                        new_child.parent = new_obj
                        scene.objects.link(new_child)
                        for mod in new_child.modifiers:
                            if mod.type == "ARMATURE":
                                mod.object = new_obj
                #If there's already a matching rig, then just update it
                elif obj["FSim"][-3:] == src_obj.name[:3]:
                    print("matching armature", armatures[obj.name])
                    TargRig = scene.objects.get(armatures[obj.name])
                    if TargRig is not None:
                        #reposition just in case
                        TargRig.animation_data_clear()
                        TargRig.location = obj.location
                        TargRig.rotation_euler = obj.rotation_euler
                        TargRig.rotation_euler.z += math.radians(self.pStartAngle)
                        print("frame, rig: ", obj.location, TargRig.location)
                        
                        #Animate
                        scene.objects.active = TargRig
                        bpy.ops.armature.fsim_run()
                
            
            #Run the simulation
        return {'FINISHED'}


#UI Panels

class ARMATURE_PT_FSim(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "FSim"
    bl_idname = "armature.fsim"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "FishSim"
    #bl_context = "objectmode"
    
    @classmethod
    def poll(cls, context):
        if context.object != None:
            return (context.mode in {'OBJECT', 'POSE'}) and (context.object.type == "ARMATURE")
        else:
            return False

    def draw(self, context):
        layout = self.layout

        obj1 = context.object
        scene = context.scene
        # row = layout.row()
        # row.label(text="Active object is: " + obj1.name)
        row = layout.row()
        row.prop(obj1, "name")
        row = layout.row()
        row.label("Animation Range")
        row = layout.row()
        row.prop(scene, "fsim_start_frame")
        row = layout.row()
        row.prop(scene, "fsim_end_frame")
        row = layout.row()
        row.operator("armature.fsim_add")
        row = layout.row()
        row.operator("armature.fsim_run")
        row = layout.row()
        row.operator("armature.fsim_populate")
        


def register():
    bpy.utils.register_class(ARMATURE_OT_FSim_Add)
    bpy.utils.register_class(ARMATURE_OT_FSim_Run)
    bpy.utils.register_class(ARMATURE_OT_FSim_Populate)
    bpy.utils.register_class(ARMATURE_PT_FSim)


def unregister():
    bpy.utils.unregister_class(ARMATURE_OT_FSim_Add)
    bpy.utils.unregister_class(ARMATURE_OT_FSim_Run)
    bpy.utils.unregister_class(ARMATURE_OT_FSim_Populate)
    bpy.utils.unregister_class(ARMATURE_PT_FSim)


if __name__ == "__main__":
    add_preset_files()
    register()
