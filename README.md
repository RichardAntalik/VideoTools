# VideoTools
Blender video editor addon

What this does:
Blender VSE UI is wrong ;)
My idea is that it should be possible to select multiple strips and modify their properties at once and many processes can be streamlined by "macros"

API:
class VideoTools - my API "namespace"
  - class Strips - idea is that instead of navigating sick blender API you can do something like Strips.allStrips().ommitStrips(Strips.selectedStrips().filterByChannel(ch)).filterByType('SOUND').getStripsEdges()
  which is less sick I guess.
  
  - class ProxyServer - does multithreaded proxy rendering


operators that kinda works:
sequencer.speedscript - add "simply" modifiable speed effect to video and audio strip cutting this clip will require custom cut operator. 
sequencer.startserver - Start multithreaded proxy rendering.
sequencer.setvolume - set volume to multiple strips
sequencer.showwaveform - show waveform of multiple strips. It may be good idea to make audio proxies(wav, or something that will process faster) though.
sequencer.move_clip_backward - move strip backward to "snap points" which are SF and EF of all strips
sequencer.move_clip_forward - guess what

there are keyboard shortcuts defined:
MoveClipBackward  'COMMA'
MoveClipForward   'PERIOD'

To make this work:
Put these files in Blender Foundation\Blender\2.79\scripts\addons\videoEdit folder

