import bpy
import socket
import os
import sys

PORT = 8081
HOST = "localhost"

class ProxyClient:
	def __init__(self):
		self.reportInterval = 20
		self.count = 0
		argv = sys.argv
		argv = argv[argv.index("--") + 1:]  # get all args after "--"

		bpy.data.scenes['Scene'].render.resolution_x = int(argv[2])
		bpy.data.scenes['Scene'].render.resolution_y = int(argv[3])
		bpy.data.scenes['Scene'].render.resolution_percentage = int(argv[4])
		bpy.data.scenes['Scene'].render.image_settings.quality = int(argv[5])
		se = bpy.context.scene.sequence_editor_create()
		clip = se.sequences.new_movie(name = "mvi", channel = 1, filepath = argv[0], frame_start = 0)
		bpy.context.scene.frame_end = clip.frame_duration

		print("client: setting output to: ", argv[1])
		bpy.data.scenes['Scene'].render.filepath = argv[1]

		bpy.app.handlers.render_stats.append(self.renderReport)
		bpy.app.handlers.render_complete.append(self.renderDone)

	def renderReport(self, dummy):
		self.count = self.count + 1

		if self.count >= self.reportInterval:
			self.count = 0
			frame = bpy.context.scene.frame_current
			total = bpy.context.scene.frame_end
			argv = sys.argv
			argv = argv[argv.index("--") + 1:]  # get all args after "--"
			videoFile = os.path.split(argv[0])[1]
			msg = videoFile + ":" + str(frame) + "/" + str(total) + "\n"
			clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			clientsocket.connect((HOST, PORT))
			clientsocket.sendall(msg.encode("utf-8"))
			clientsocket.shutdown(1)
			clientsocket.close()

	def renderDone(self, dummy):
		argv = sys.argv
		argv = argv[argv.index("--") + 1:]  # get all args after "--"
		videoFile = os.path.split(argv[0])[1]
		msg = videoFile + ":done"

		clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		clientsocket.connect((HOST, PORT))
		clientsocket.sendall(msg.encode("utf-8"))
		clientsocket.shutdown(1)
		clientsocket.close()

if __name__ == "__main__":
	pc = ProxyClient()