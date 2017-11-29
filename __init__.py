import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )

bl_info = {
    "name": "VideoTools",
    "category": "Sequencer",
    }

class MoveClipBackward(bpy.types.Operator):
    """move clip backward"""      
    bl_idname = "sequencer.move_clip_backward"        
    bl_label = "move clip backward"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        allSequencesEdges = []
        for seq in context.sequences:
            allSequencesEdges.append(seq.frame_start)
            allSequencesEdges.append(seq.frame_final_end)
            allSequencesEdges.sort()

        allSequencesEdges.reverse()
        print(allSequencesEdges)

        selectedFrameStart = context.selected_sequences[0].frame_start
        newFrameStart = 0

        for frameStart in allSequencesEdges:
            if selectedFrameStart > frameStart:
                print(selectedFrameStart)
                print(newFrameStart)
                newFrameStart = frameStart
                break

        context.selected_sequences[0].frame_start = newFrameStart
        return {'FINISHED'}

class MoveClipForward(bpy.types.Operator):
    """move clip forward"""
    bl_idname = "sequencer.move_clip_forward"
    bl_label = "move clip forward"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        allSequencesEdges = []
        for seq in context.sequences:
            allSequencesEdges.append(seq.frame_start)
            allSequencesEdges.append(seq.frame_final_end)
            allSequencesEdges.sort()

        print(allSequencesEdges)

        selectedFrameStart = context.selected_sequences[0].frame_start
        newFrameStart = selectedFrameStart

        for frameStart in allSequencesEdges:
            if selectedFrameStart < frameStart:
                print(selectedFrameStart)
                print(newFrameStart)
                newFrameStart = frameStart
                break

        context.selected_sequences[0].frame_start = newFrameStart
        return {'FINISHED'}

class VideoTools():
    def getSelectedStrips(context):
        pass

    def getStripByName(context, name):
        return context.scene.sequence_editor.sequences_all[name]

    def getSequencerSnapPoints(context):
        return {'FINISHED'}

    def getAudioStripBySelectedMovieStrip(context):
        for seq in context.sequences:
            selectedFrameStart = context.selected_sequences[0].frame_start
            if seq.frame_start == selectedFrameStart:
                if seq.type == 'SOUND':
                    return seq

    def getSequencerArea(context):
        screens = [context.screen]
        for screen in screens:
            for area in screen.areas:
                if area.type == 'SEQUENCE_EDITOR':
                    return area
    def removeSpeedFx(context):
        scene = context.scene
        activeStrip = scene.sequence_editor.active_strip
        area = VideoTools.getSequencerArea(context)

        try:
            SpeedFxName = activeStrip['SpeedFxName']
        except KeyError:
            SpeedFxName = ""
        else:
            try:
                effect = VideoTools.getStripByName(context, SpeedFxName)
            except:
                pass
            else:
                activeStrip.select = False
                effect.select = True
                bpy.ops.sequencer.delete({'area': area})
                activeStrip.select = True
        activeStrip["SpeedFxName"] = ""

    def addSpeedFx(context, speed):
        VideoTools.removeSpeedFx(context)
        
        scene = context.scene
        activeStrip = scene.sequence_editor.active_strip
        area = VideoTools.getSequencerArea(context)
        try:
            duration = scene.sequence_editor.active_strip['originalLength']
        except KeyError:
            duration = scene.sequence_editor.active_strip.frame_final_duration
            scene.sequence_editor.active_strip['originalLength'] = duration

        scene.sequence_editor.active_strip['clipSpeed'] = speed
        newDuration = activeStrip["originalLength"] / speed
        activeStrip.frame_final_duration = newDuration
        if speed != 1:
            effect = scene.sequence_editor.sequences.new_effect(
                name= "SPD:" + activeStrip.name,
                type="SPEED",
                channel=31,
                frame_start=1,
                frame_end=0,
                seq1=activeStrip)
            effect.use_default_fade = False
            effect.speed_factor = 1
            effect.multiply_speed = speed
            activeStrip["SpeedFxName"] = effect.name
        audio = VideoTools.getAudioStripBySelectedMovieStrip(context)
        audio.frame_final_duration = newDuration
        audio.pitch = speed

        audioLockBefore = audio.lock
        activeStripLockBefore = activeStrip.lock
        audio.lock = True
        activeStrip.lock = True
        for x in range(31):
            bpy.ops.transform.seq_slide({'area':area}, value = (0,-1))
        audio.lock = audioLockBefore
        activeStrip.lock = activeStripLockBefore

class SpeedScript(bpy.types.Operator):
    bl_idname = "sequencer.speedscript"        
    bl_label = "select sound strip"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            speed = context.scene.sequence_editor.active_strip["clipSpeed"]
        except KeyError:
            speed = context.scene.vt_props.clipSpeed
        VideoTools.addSpeedFx(context, speed)
        return {'FINISHED'}

class VTprops(bpy.types.PropertyGroup):
    clipSpeed = bpy.props.FloatProperty(
        name = "My options",
        default = 1.0,
        soft_min = 0.1,
        soft_max = 20,
        step = 5,
        description = "My enum description",
    )

class OBJECT_PT_StripToolsPanel(Panel):
    bl_idname = "OBJECT_PT_StripToolsPanel"
    bl_label = "Strip Tools Panel"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'   

    @classmethod
    def poll(cls, context):
        return (context.scene.sequence_editor.active_strip.type == 'MOVIE')
   
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        try:
            layout.prop(scene.sequence_editor.active_strip, '["clipSpeed"]', text="Clip Speed (legit)")
            blah = scene.sequence_editor.active_strip["clipSpeed"]     #above handled exception so throw new one
        except KeyError:
            layout.prop(scene.vt_props, "clipSpeed", text="Clip Speed (fake)")
        layout.operator("sequencer.speedscript", text="Run speed script")

def register():
    bpy.utils.register_module(__name__)

    bpy.types.Scene.vt_props = bpy.props.PointerProperty(type=VTprops)

    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps.new(name='Frames')
    kmi = km.keymap_items.new(MoveClipBackward.bl_idname, 'COMMA', 'PRESS', ctrl=False, shift=False)
    kmi = km.keymap_items.new(MoveClipForward.bl_idname, 'PERIOD', 'PRESS', ctrl=False, shift=False)

def unregister():
    bpy.utils.unregister_module(__name__)
    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps['Frames']
    km.keymap_items.remove(km.keymap_items[MoveClipBackward.bl_idname])
    km.keymap_items.remove(km.keymap_items[MoveClipForward.bl_idname])

if __name__ == "__main__":
    register()