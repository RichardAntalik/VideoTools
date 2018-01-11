import bpy
import inspect
import subprocess
import socket
import re
import os
import threading

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


class VTprops(bpy.types.PropertyGroup):
	pass


class VideoTools():
	"""Utility class"""

	class Strips():
		"""
		list of strips

		Provides additional tools for strips - filtering, selecting, iterators...
		strips: a list of strips

		"""

		def __init__(self, context, strips = []):
			self.context = context
			self.strips = list(strips)	#list of strips
			self.i = -1			 #iterator index

		def __iter__(self):
			return self

		def __next__(self):
			if self.i >= len(self.strips)-1:
				self.i = -1
				raise StopIteration
			self.i = self.i + 1
			
			return self.strips[self.i]
		
		def __getitem__(self, key):
			return self.strips[key]

		def __len__(self):
			return len(self.strips)

		def ommitStrips(self, strips):
			newStrips = self.strips
			try:
				for strip in strips:
					newStrips.remove(strip)
			except TypeError:
				newStrips.remove(strips)
			return VideoTools.Strips(self.context, newStrips)

		def addStrips(self, strips):
			"""
			add strips to list
			strips: Strips object
			"""
			try:
				newStrips = VideoTools.Strips(self.context, self.strips + strips.strips)
			except AttributeError:
				newStrips =  VideoTools.Strips(self.context, self.strips + [strips])
			return newStrips

		def intersect(self, strips):
			"""
			intersect this strips instance with another one
			strips: Strips object
			"""
			return VideoTools.Strips(self.context, list(self.strips & strips.strips))

		def filterByChannel(self, channel):
			"""
			filter strips by channel in which they are
			"""
			newStrips = []
			for strip in self.strips:
				if strip.channel == channel:
					newStrips.append(strip)
			return VideoTools.Strips(self.context, newStrips)

		def filterBySelected(self):
			"""

			"""
			return self.intersect(self, self.selectedStrips())
		def allStrips(self):
			"""
			"""
			return VideoTools.Strips(self.context, self.context.scene.sequence_editor.sequences_all)

		def selectedStrips(self):
			"""

			"""
			return VideoTools.Strips(self.context, self.context.selected_sequences)

		def filterByRegex(self, property, regex):
			pass

		def selectNone(self):
			for strip in self.allStrips():
				strip.select = False

		def selectAll(self):
			for strip in self.allStrips():
				strip.select = True

		def select(self):
			for strip in self:
				strip.select = True

		def sortBySF(self):
			sortedStrips = sorted(self.strips, key= lambda strip: strip.frame_final_start)
			return VideoTools.Strips(self.context, sortedStrips)

		def sortByEF(self):
			sortedStrips = sorted(self.strips, key= lambda strip: strip.frame_final_end)
			return VideoTools.Strips(self.context, sortedStrips)
		def getStripsEdges(self):
			"""
			Returns sorted list of final ends and starts of strips(sequencer position)
			"""
			StripsEdges = []
			for strip in self:
				StripsEdges.append(strip.frame_final_start)
				StripsEdges.append(strip.frame_final_end)
			StripsEdges.sort()
			return StripsEdges
		def getStripsChannels(self):
			"""
			Returns sorted list of final ends and starts of strips(sequencer position)
			"""
			StripsChannels = []
			for strip in self:
				StripsChannels.append(strip.channel)
			StripsChannels.sort()
			return list(set(StripsChannels))

		def moveUp(self, distance):
			bpy.ops.transform.seq_slide({'area':self.context.area}, value = (0,distance))

		def moveStripsBackward(self):
			firstStrip = self.sortBySF()[0]
			newFrameFinalStart = 0
			for edge in reversed(self.allStrips().getStripsEdges()):
				if firstStrip.frame_final_start > edge:
					newFrameFinalStart = edge
					break
			distance = newFrameFinalStart - firstStrip.frame_start - firstStrip.frame_offset_start

			for strip in self:
				strip.frame_start = strip.frame_start + distance

		def moveStripsForward(self):
			firstStrip = self.sortBySF()[0]
			for edge in self.allStrips().ommitStrips(self.selectedStrips()).getStripsEdges():
				if firstStrip.frame_final_start < edge:
					newFrameFinalStart = edge
					break
			try:
				distance = newFrameFinalStart - firstStrip.frame_start - firstStrip.frame_offset_start
			except NameError: 
				distance = 0

			for strip in self:
				strip.frame_start = strip.frame_start + distance

		def setVolume(self, volume):
			for strip in self:
				try:
					strip.volume = volume
				except AttributeError:
					pass
		def doForEach(self, callback):
			for strip in self:
				callback(strip)

		def showWaveform(self, value):
			for strip in self:
				try:
					strip.show_waveform = value
				except AttributeError:
					pass

		def getAudioStripByMovieStrip(self, strip):
			for seq in self.allStrips().filterByType('SOUND'):
				if seq.frame_start == strip.frame_start:
					if seq.frame_offset_start == strip.frame_offset_start:
						return seq

		def getStripByName(self, name):
			return self.context.scene.sequence_editor.sequences_all[name]

		def setSpeed(self, speed):
#			lastChannel = 0
#			for movieStrip in self.filterByType('MOVIE'):		#move strips up
#				channel = movieStrip.channel
#				if channel == lastChannel:
#					continue
#				lastChannel = channel
#				self.selectNone()
#				for strip in self.allStrips():
#					if strip.channel > channel: 
#						strip.select = True
#				self.selectedStrips().moveUp(1)
#			self.selectNone()
#			self.select()

			for strip in self.filterByType('MOVIE'):
				try:
					duration = strip['originalLength']
				except KeyError:
					duration = strip.frame_final_duration
					strip['originalLength'] = duration

				strip['clipSpeed'] = speed
				newDuration = strip["originalLength"] / speed
				strip.frame_final_duration = newDuration

				try:
					effect = self.getStripByName(strip['SpeedFxName'])
				except KeyError:
					effect = self.context.scene.sequence_editor.sequences.new_effect(
						name= "SPD:" + strip.name,
						type="SPEED",
						frame_start=1,
						frame_end=0,
						channel = strip.channel + 1,
						seq1=strip)

				effect.use_default_fade = False
				effect.speed_factor = 1
				effect.multiply_speed = speed
				strip["SpeedFxName"] = effect.name

				audio = self.getAudioStripByMovieStrip(strip)
				audio.frame_final_duration = newDuration
				audio.pitch = speed


		def isTypeInList(self, type):
			for strip in self:
				if strip.type == type:
					return True
			return False

		def filterByType(self, type):
			newStrips = VideoTools.Strips(self.context)
			for strip in self:
				if strip.type == type:
					newStrips = newStrips.addStrips(strip)
			return newStrips

		def invertSelection(self):
			for strip in self:
				strip.select = (not strip.select)

		def setProxyFiftyOnlyNoOverwrite(self):
			for strip in self:
				strip.use_proxy = True
				strip.proxy.build_50 = True
				strip.proxy.build_25 = False
				strip.proxy.build_75 = False
				strip.proxy.build_100 = False
				strip.proxy.use_overwrite = False

#	def removeSpeedFx(context):
#		scene = context.scene
#		activeStrip = scene.sequence_editor.active_strip
#		area = VideoTools.getSequencerArea(context)
#
#		try:
#			SpeedFxName = activeStrip['SpeedFxName']
#		except KeyError:
#			SpeedFxName = ""
#		else:
#			try:
#				effect = VideoTools.getStripByName(context, SpeedFxName)
#			except:
#				pass
#			else:
#				activeStrip.select = False
#				effect.select = True
#				bpy.ops.sequencer.delete({'area': area})
#				activeStrip.select = True
#		activeStrip["SpeedFxName"] = ""

	class ProxyServer:
		def __init__(self, context):
			import multiprocessing

			strips = VideoTools.Strips(context)
			allStrips = strips.allStrips().filterByType('MOVIE')

			allStrips.setProxyFiftyOnlyNoOverwrite()
			self.se = bpy.context.scene.sequence_editor_create()

			self.cpuCores = multiprocessing.cpu_count()
			self.port = 8081
			self.host = "localhost"
			self.clientBlend = "1.blend"
			self.clientScript = "client.py"

			self.context = context
			self.clientsRunning = 0
			self.lock = False
			self.scriptPath = re.findall('.*\\\\', inspect.getfile(inspect.currentframe()))[0]
			self.blenderBinary = bpy.app.binary_path
			self.videoFiles = list(set([strip.filepath for strip in allStrips]))
			self.proxyStorage = self.se.proxy_storage
			self.filesTotal = len(self.videoFiles)
			self.doneTotal = 0
			self.startServer()

		def startServer(self):
			try:
				serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				serversocket.bind((self.host, self.port))
				serversocket.listen(1)
#				self.report({"INFO"}, "Listening on %s:%s" % (self.host, self.port))
				self.serversocket = serversocket
				threading.Thread(target = self.listenToClients).start()
			except OSError:
				pass

		def listenToClients(self):
			while self.doneTotal < self.filesTotal:
#				print("listening...\n")
				if self.clientsRunning < self.cpuCores:
					self.startClient()
					
				connection, address = self.serversocket.accept()
				buf = connection.recv(4096).decode("utf-8")
				msg = buf.split(":")
				
				if msg[1] == "done" :
					print("Done:", self.doneTotal, "/", self.filesTotal)
					self.clientsRunning = self.clientsRunning - 1
					self.doneTotal = self.doneTotal + 1
				else:
					print("Done:", self.doneTotal, "/", self.filesTotal, "processing:", buf )

			if self.doneTotal >= self.filesTotal:
				self.serversocket.close()
				self.rebuildProxies()
#				print("dying...\n")


		def rebuildProxies(self):
			bpy.ops.sequencer.rebuild_proxy()


		def startClient(self):
			try:
				current = self.videoFiles.pop(0)
			except IndexError:
				pass
			else:
				videoPath = bpy.path.abspath(current)
				videoDir = os.path.split(videoPath)[0]
				videoFile = os.path.split(videoPath)[1]
				if self.proxyStorage == "PROJECT":
					proxyDir = bpy.path.abspath(self.se.proxy_dir)
				else:
					proxyDir = videoDir + '\\BL_proxy\\'

				command = self.blenderBinary 
				command += ' --background '
				command += ' "' + self.scriptPath + self.clientBlend + '" '
				command += ' --python'
				command += ' "' + self.scriptPath + self.clientScript + '" '
				command += ' --render-anim'
				command += ' -- '
				command += ' "' + videoPath + '" '
				command += ' "'+ proxyDir + videoFile + "\\proxy_50.avi" +'" '
				command += ' "'+ str(bpy.data.scenes['Scene'].render.resolution_x) +'" '
				command += ' "'+ str(bpy.data.scenes['Scene'].render.resolution_y) +'" '
				command += ' "'+ str(self.context.scene.vt_props.resRatio) +'" '
				command += ' "'+ str(self.context.scene.vt_props.quality) +'" '

	#			self.report({"INFO"}, "running: " + command)

				with open(os.devnull, 'w') as tempf:
					proc = subprocess.Popen(command, stdout=tempf, stderr=tempf)	#silent mode
#					proc = subprocess.Popen(command)

				self.clientsRunning = self.clientsRunning + 1

class StartServer(bpy.types.Operator):

	VTprops.quality = bpy.props.IntProperty(
		name = "Quality",
		default = 50,
		soft_min = 1,
		soft_max = 100,
		step = 5
	)
	VTprops.resRatio = bpy.props.IntProperty(
		name = "Resolution ratio",
		default = 50,
		soft_min = 25,
		soft_max = 100,
		step = 25
	)

	bl_idname = "sequencer.startserver"
	bl_options = {'REGISTER'}
	bl_label = "Start server"

	def execute(self, context):
		ps = VideoTools.ProxyServer(context)
		return {'FINISHED'}

class MoveClipBackward(bpy.types.Operator):
	"""move clip backward"""	  
	bl_idname = "sequencer.move_clip_backward"		
	bl_label = "move clip backward"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		VideoTools.Strips(context).selectedStrips().moveStripsBackward()
		return {'FINISHED'}

class MoveClipForward(bpy.types.Operator):
	"""move clip forward"""
	bl_idname = "sequencer.move_clip_forward"
	bl_label = "move clip forward"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		VideoTools.Strips(context).selectedStrips().moveStripsForward()
		return {'FINISHED'}

class SoundVolumeScript(bpy.types.Operator):
	bl_idname = "sequencer.setvolume"		
	bl_options = {'REGISTER', 'UNDO'}
	bl_label = "SoundVolumeScript"

	VTprops.volume = bpy.props.FloatProperty(
		name = "Sound clip volume",
		default = 1.0,
		soft_min = 0.0,
		soft_max = 3,
		step = 1,
		update=lambda self, context: SoundVolumeScript.execute(self, context)
	)

	def execute(self, context):
		VideoTools.Strips(context).selectedStrips().setVolume(context.scene.vt_props.volume)
		return {'FINISHED'}

class ShowWaveform(bpy.types.Operator):
	bl_idname = "sequencer.showwaveform"		
	bl_options = {'REGISTER', 'UNDO'}
	bl_label = "show waveform"

	VTprops.showWaveform = bpy.props.BoolProperty(
		name = "Show Waveform",
		default = False,
		update=lambda self, context: ShowWaveform.execute(self, context)
	)

	def execute(self, context):
		VideoTools.Strips(context).selectedStrips().showWaveform(context.scene.vt_props.showWaveform)
		return {'FINISHED'}

class SpeedScript(bpy.types.Operator):
	bl_idname = "sequencer.speedscript"		
	bl_options = {'REGISTER', 'UNDO'}
	bl_label = "SpeedScript"

	VTprops.clipSpeed = bpy.props.FloatProperty(
		name = "Clip speed",
		default = 1.0,
		soft_min = 0.1,
		soft_max = 20,
		step = 5
	)

	def execute(self, context):
		try:
			speed = context.scene.sequence_editor.active_strip["clipSpeed"]
		except KeyError:
			speed = context.scene.vt_props.clipSpeed
		VideoTools.Strips(context).selectedStrips().setSpeed(speed)
		return {'FINISHED'}


class SendMsg(bpy.types.Operator):
	bl_idname = "sequencer.sendmsg"		
	bl_options = {'REGISTER'}
	bl_label = "Send server message"

	def execute(self, context):
		PORT = 8081
		HOST = "localhost"

		clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		clientsocket.connect((HOST, PORT))
		clientsocket.sendall("ty vole".encode("utf-8") + b'\x00')
		clientsocket.shutdown(1)
		clientsocket.close()
		return {'FINISHED'}

class KeepSelectionCut(bpy.types.Operator):
	bl_idname = "sequencer.keepselectioncut"		
	bl_options = {'REGISTER', 'UNDO'}
	bl_label = "KeepSelectionCut"

	def execute(self, context):
#		bpy.ops.sequencer.cut()
		return {'FINISHED'}


class OBJECT_PT_SoundToolsPanel(Panel):
	bl_idname = "OBJECT_PT_SoundToolsPanel"
	bl_label = "Sound Tools Panel"
	bl_space_type = 'SEQUENCE_EDITOR'
	bl_region_type = 'UI'   

	@classmethod
	def poll(self, context):
		return VideoTools.Strips(context).selectedStrips().isTypeInList('SOUND')
   
	def draw(self, context):
		layout = self.layout
		scene = context.scene
		layout.prop(scene.vt_props, "volume", text="Selected clips Volume")
		layout.prop(scene.vt_props, "showWaveform", text="Show waveform")

class OBJECT_PT_StripToolsPanel(Panel):
	bl_idname = "OBJECT_PT_StripToolsPanel"
	bl_label = "Strip Tools Panel"
	bl_space_type = 'SEQUENCE_EDITOR'
	bl_region_type = 'UI'   

	@classmethod
	def poll(self, context):
		return VideoTools.Strips(context).selectedStrips().isTypeInList('MOVIE')
   
	def draw(self, context):
		layout = self.layout
		scene = context.scene
		try:
			layout.prop(scene.sequence_editor.active_strip, '["clipSpeed"]', text="Clip Speed (legit)")
			blah = scene.sequence_editor.active_strip["clipSpeed"]	 #above handled exception so throw new one
		except KeyError:
			layout.prop(scene.vt_props, "clipSpeed", text="Clip Speed (fake)")
		layout.operator("sequencer.speedscript", text="Run speed script")
#		layout.operator("sequencer.sendmsg", text="send server a message")

		layout.prop(scene.vt_props, "resRatio", text="Resolution ratio")
		layout.prop(scene.vt_props, "quality", text="Quality")
		layout.operator("sequencer.startserver", text="Make proxies")



def register():
	bpy.utils.register_module(__name__)
	bpy.types.Scene.vt_props = bpy.props.PointerProperty(type=VTprops)

	kc = bpy.context.window_manager.keyconfigs.addon
	km = kc.keymaps.new(name='Frames')
#	km = kc.keymaps['Sequencer']
	kmi = km.keymap_items.new(MoveClipBackward.bl_idname, 'COMMA', 'PRESS', ctrl=False, shift=False)
	kmi = km.keymap_items.new(MoveClipForward.bl_idname, 'PERIOD', 'PRESS', ctrl=False, shift=False)
	#kmi = km.keymap_items.new(KeepSelectionCut.bl_idname, 'K', 'PRESS', ctrl=False, shift=False)

def unregister():
	bpy.utils.unregister_module(__name__)
	kc = bpy.context.window_manager.keyconfigs.addon
	km = kc.keymaps['Frames']
	km.keymap_items.remove(km.keymap_items[MoveClipBackward.bl_idname])
	km.keymap_items.remove(km.keymap_items[MoveClipForward.bl_idname])
	#km.keymap_items.remove(km.keymap_items[KeepSelectionCut.bl_idname])

if __name__ == "__main__":
	register()